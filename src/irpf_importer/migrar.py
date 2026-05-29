from __future__ import annotations

import json
import re
import tempfile
from dataclasses import asdict, dataclass, replace
from datetime import datetime
from pathlib import Path
import xml.etree.ElementTree as ET

from .clone import BLANK_CPF, format_cpf, only_digits, unformat_cpf
from .conf import recalcular_conf
from .importers.bens import ImportStats as BensStats, import_bens
from .importers.proventos import ProventosStats, import_proventos
from .xml_utils import NS, q

ET.register_namespace("", NS)

IDENTIFIER_TAGS = ("identificadorDec", "identificadorDeclaracao", "copiaIdentificador")
RECEIPT_ATTRS = ("numeroReciboDecAnterior", "numReciboDecRetif", "numReciboTransmitido")
TRANSMISSION_ATTRS = ("transmitida", "tpTransmitida", "declaracaoRetificadora")


@dataclass(frozen=True)
class ReferenceStats:
    referencia_xml: Path | None
    base_xml_2026: Path
    classe_referencia: str
    classe_base_2026: str
    tipo_itens_referencia_prefix: str
    tipo_itens_base_prefix: str
    bens_referencia_total_itens: str
    bens_base_total_itens: str
    bens_referencia_total_atual: str
    bens_base_total_anterior: str


@dataclass(frozen=True)
class MigrationStats:
    dry_run: bool
    base_xml_2026: Path
    referencia_xml_2025: Path | None
    target_xml: Path
    target_conf: Path
    target_cpf: str
    target_name: str
    receipts_cleared: int
    identifiers_updated: int
    cpf_beneficiario_updated: int
    reference: ReferenceStats
    bens: BensStats | None
    proventos: ProventosStats | None
    report_path: Path | None = None


@dataclass(frozen=True)
class MigrationResult:
    stats: MigrationStats


def _tag_name(element: ET.Element) -> str:
    return element.tag.split("}")[-1]


def _read_source_identity(root: ET.Element, xml_path: Path) -> tuple[str, str]:
    for tag in ("identificadorDeclaracao", "identificadorDec", "copiaIdentificador"):
        el = root.find(f".//{q(tag)}")
        if el is not None:
            cpf = only_digits(el.attrib.get("cpf"))
            nome = (el.attrib.get("nome") or "").strip()
            if cpf:
                return cpf, nome
    m = re.search(r"(\d{11})", xml_path.name)
    return (m.group(1) if m else "00000000000", "")


def _read_cpf_from_filename(path: Path) -> str | None:
    m = re.search(r"(\d{11})", path.name)
    return m.group(1) if m else None


def _target_paths(base_xml_2026: Path, target_dir: Path, target_cpf: str | None) -> tuple[str, Path, Path]:
    cpf_digits = unformat_cpf(target_cpf) if target_cpf else (_read_cpf_from_filename(base_xml_2026) or "00000000000")
    folder = target_dir / cpf_digits
    xml = folder / f"{cpf_digits}-0000000000.xml"
    conf = xml.with_suffix(".conf")
    return cpf_digits, xml, conf


def _first_or_empty(root: ET.Element, tag: str, attr: str) -> str:
    el = root.find(f".//{q(tag)}")
    if el is None:
        return ""
    return el.attrib.get(attr, "")


def _tipo_prefix(root: ET.Element) -> str:
    for el in root.iter():
        tipo = el.attrib.get("tipoItens")
        if tipo:
            if ".negocio." in tipo:
                return "serpro.ppgd.irpf.negocio"
            if ".irpf." in tipo:
                return "serpro.ppgd.irpf"
            return tipo.rsplit(".", 1)[0]
    return ""


def _reference_stats(base_xml_2026: Path, referencia_xml_2025: Path | None) -> ReferenceStats:
    base_root = ET.parse(base_xml_2026).getroot()
    ref_root = ET.parse(referencia_xml_2025).getroot() if referencia_xml_2025 else None

    def bens_attr(root: ET.Element | None, attr: str) -> str:
        if root is None:
            return ""
        bens = root.find(f".//{q('bens')}")
        return bens.attrib.get(attr, "") if bens is not None else ""

    return ReferenceStats(
        referencia_xml=referencia_xml_2025,
        base_xml_2026=base_xml_2026,
        classe_referencia=ref_root.attrib.get("classeJava", "") if ref_root is not None else "",
        classe_base_2026=base_root.attrib.get("classeJava", ""),
        tipo_itens_referencia_prefix=_tipo_prefix(ref_root) if ref_root is not None else "",
        tipo_itens_base_prefix=_tipo_prefix(base_root),
        bens_referencia_total_itens=bens_attr(ref_root, "totalItens"),
        bens_base_total_itens=bens_attr(base_root, "totalItens"),
        bens_referencia_total_atual=bens_attr(ref_root, "totalExercicioAtual"),
        bens_base_total_anterior=bens_attr(base_root, "totalExercicioAnterior"),
    )


def prepare_xml_2026_for_update(
    root: ET.Element,
    *,
    xml_path: Path,
    target_cpf: str | None = None,
    target_name: str | None = None,
    clear_receipts: bool = False,
) -> tuple[str, str, int, int, int]:
    """Prepara um XML 2026 já reconhecido pelo programa da Receita para receber dados atualizados.

    Esta função NÃO tenta converter XML 2025 para 2026. Ela preserva a estrutura do XML base 2026
    e atualiza dados fiscais/identidade somente quando solicitado. Por padrão, preserva recibos/metadados do XML 2026 base.
    """
    source_cpf, source_name = _read_source_identity(root, xml_path)
    cpf_digits = unformat_cpf(target_cpf) if target_cpf else source_cpf
    cpf_fmt = format_cpf(cpf_digits) if len(cpf_digits) == 11 else BLANK_CPF
    name = target_name if target_name is not None else source_name
    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    root.attrib["dataHoraSalvamento"] = now
    root.attrib["utlimoCPFAutenticado"] = BLANK_CPF

    receipts_cleared = 0
    identifiers_updated = 0
    cpf_beneficiario_updated = 0

    for tag in IDENTIFIER_TAGS:
        for ident in root.findall(f".//{q(tag)}"):
            if target_cpf and ident.attrib.get("cpf") != cpf_fmt:
                ident.attrib["cpf"] = cpf_fmt
                identifiers_updated += 1
            if target_name is not None and ident.attrib.get("nome") != name:
                ident.attrib["nome"] = name
                identifiers_updated += 1
            if clear_receipts:
                for attr in RECEIPT_ATTRS:
                    if ident.attrib.get(attr):
                        ident.attrib[attr] = ""
                        receipts_cleared += 1
                for attr in TRANSMISSION_ATTRS:
                    if attr in ident.attrib:
                        ident.attrib[attr] = "0" if attr in {"transmitida", "declaracaoRetificadora"} else ""
                ident.attrib["dataUltimoAcesso"] = now

    if target_cpf:
        for element in root.iter():
            if "cpfBeneficiario" in element.attrib and element.attrib.get("cpfBeneficiario") != cpf_fmt:
                element.attrib["cpfBeneficiario"] = cpf_fmt
                cpf_beneficiario_updated += 1

    return cpf_digits, name, receipts_cleared, identifiers_updated, cpf_beneficiario_updated


# Compatibilidade com testes/código antigo.
def prepare_xml_for_next_year(root: ET.Element, *, target_cpf: str | None = None, target_name: str | None = None, clear_receipts: bool = False) -> tuple[str, str, int, int, int]:
    return prepare_xml_2026_for_update(root, xml_path=Path("declaracao.xml"), target_cpf=target_cpf, target_name=target_name, clear_receipts=clear_receipts)


def _stats_to_report(stats: MigrationStats) -> dict[str, object]:
    data = asdict(stats)
    for key in ("base_xml_2026", "referencia_xml_2025", "target_xml", "target_conf", "report_path"):
        if data.get(key) is not None:
            data[key] = str(data[key])
    if data.get("reference"):
        ref = data["reference"]
        if isinstance(ref, dict):
            for key in ("referencia_xml", "base_xml_2026"):
                if ref.get(key) is not None:
                    ref[key] = str(ref[key])
    return data


def migrate_declaration(
    *,
    base_xml_2026: Path | None = None,
    referencia_xml_2025: Path | None = None,
    # source_xml permanece por compatibilidade; se usado, é tratado como base XML 2026.
    source_xml: Path | None = None,
    target_dir: Path,
    irpf_dir: Path | None = None,
    bens_file: Path | None = None,
    proventos_file: Path | None = None,
    target_cpf: str | None = None,
    target_name: str | None = None,
    clear_receipts: bool = False,
    recalc_conf: bool = True,
    dry_run: bool = False,
    bens_mode: str = "upsert",
    proventos_mode: str = "replace",
    report_path: Path | None = None,
) -> MigrationResult:
    if base_xml_2026 is None:
        base_xml_2026 = source_xml
    if base_xml_2026 is None:
        raise ValueError("Informe --base-xml-2026. O XML 2025 deve ser usado apenas como referência.")

    base_xml_2026 = Path(base_xml_2026)
    referencia_xml_2025 = Path(referencia_xml_2025) if referencia_xml_2025 is not None else None
    target_dir = Path(target_dir)

    if not base_xml_2026.exists():
        raise FileNotFoundError(base_xml_2026)
    if referencia_xml_2025 is not None and not referencia_xml_2025.exists():
        raise FileNotFoundError(referencia_xml_2025)
    if bens_file is not None and not Path(bens_file).exists():
        raise FileNotFoundError(bens_file)
    if proventos_file is not None and not Path(proventos_file).exists():
        raise FileNotFoundError(proventos_file)
    if recalc_conf and not dry_run:
        if irpf_dir is None:
            raise RuntimeError("--irpf-dir é obrigatório para recalcular o .conf.")
        if not Path(irpf_dir).exists():
            raise FileNotFoundError(irpf_dir)

    inferred_cpf = target_cpf or _read_cpf_from_filename(base_xml_2026)
    _cpf_digits, intended_xml, intended_conf = _target_paths(base_xml_2026, target_dir, inferred_cpf)
    ref_stats = _reference_stats(base_xml_2026, referencia_xml_2025)

    def run_pipeline(work_xml: Path, *, write_final: bool) -> tuple[str, str, int, int, int, BensStats | None, ProventosStats | None]:
        tree = ET.parse(base_xml_2026)
        root = tree.getroot()
        final_cpf, final_name, receipts, identifiers, cpf_benef = prepare_xml_2026_for_update(
            root,
            xml_path=base_xml_2026,
            target_cpf=target_cpf,
            target_name=target_name,
            clear_receipts=clear_receipts,
        )
        work_xml.parent.mkdir(parents=True, exist_ok=True)
        tree.write(work_xml, encoding="utf-8", xml_declaration=True)

        bens_stats = None
        proventos_stats = None
        if bens_file is not None:
            bens_stats = import_bens(work_xml, Path(bens_file), mode=bens_mode, write=True)
        if proventos_file is not None:
            proventos_stats = import_proventos(work_xml, Path(proventos_file), mode=proventos_mode, write=True)

        if write_final:
            if recalc_conf:
                recalcular_conf(Path(irpf_dir), work_xml)  # type: ignore[arg-type]
            else:
                work_xml.with_suffix(".conf.pending").write_text(
                    "CONF pendente: execute recálculo antes de abrir no IRPF.\n",
                    encoding="utf-8",
                )
        return final_cpf, final_name, receipts, identifiers, cpf_benef, bens_stats, proventos_stats

    if dry_run:
        with tempfile.TemporaryDirectory(prefix="irpf_migrar_") as tmp:
            tmp_xml = Path(tmp) / intended_xml.name
            final_cpf, final_name, receipts, identifiers, cpf_benef, bens_stats, proventos_stats = run_pipeline(tmp_xml, write_final=False)
    else:
        final_cpf, final_name, receipts, identifiers, cpf_benef, bens_stats, proventos_stats = run_pipeline(intended_xml, write_final=True)

    stats = MigrationStats(
        dry_run=dry_run,
        base_xml_2026=base_xml_2026,
        referencia_xml_2025=referencia_xml_2025,
        target_xml=intended_xml,
        target_conf=intended_conf,
        target_cpf=final_cpf,
        target_name=final_name,
        receipts_cleared=receipts,
        identifiers_updated=identifiers,
        cpf_beneficiario_updated=cpf_benef,
        reference=ref_stats,
        bens=bens_stats,
        proventos=proventos_stats,
        report_path=report_path,
    )

    if report_path is not None and not dry_run:
        report_path = Path(report_path)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(_stats_to_report(stats), ensure_ascii=False, indent=2), encoding="utf-8")
        stats = replace(stats, report_path=report_path)

    return MigrationResult(stats=stats)


def print_result(result: MigrationResult) -> None:
    s = result.stats
    if s.dry_run:
        print("DRY-RUN: nenhum arquivo final foi gravado e o .conf não foi recalculado.")
    print("Migração para IRPF 2026")
    print(f"XML base 2026: {s.base_xml_2026}")
    if s.referencia_xml_2025:
        print(f"XML referência 2025: {s.referencia_xml_2025}")
    print(f"XML destino: {s.target_xml}")
    print(f"CONF destino: {s.target_conf}")
    print(f"CPF destino: {s.target_cpf}")
    print(f"Nome destino: {s.target_name}")
    print(f"Recibos limpos: {s.receipts_cleared}")
    if s.receipts_cleared == 0:
        print("Recibos preservados: sim")
    print(f"Identificadores atualizados: {s.identifiers_updated}")
    print(f"cpfBeneficiario atualizados: {s.cpf_beneficiario_updated}")
    print("Estrutura:")
    print(f"  classe base 2026: {s.reference.classe_base_2026}")
    if s.reference.classe_referencia:
        print(f"  classe referência 2025: {s.reference.classe_referencia}")
        print(f"  tipoItens base: {s.reference.tipo_itens_base_prefix}")
        print(f"  tipoItens referência: {s.reference.tipo_itens_referencia_prefix}")
    if s.bens is not None:
        b = s.bens
        print("Bens e Direitos:")
        print(f"  Adicionados: {b.added} | Atualizados: {b.updated} | Removidos: {b.removed}")
        print(f"  Duplicados consolidados: {b.consolidated_duplicates} | Chaves ambíguas: {b.ambiguous_keys} | Ignorados ambíguos: {b.skipped_ambiguous}")
        print(f"  Total itens: {b.total_items}")
        print(f"  Totais: anterior={b.total_exercicio_anterior} atual={b.total_exercicio_atual}")
    if s.proventos is not None:
        p = s.proventos
        print("Proventos:")
        print(f"  Isentos adicionados: {p.isentos_added} | JCP adicionados: {p.jcp_added} | Ignorados: {p.ignored}")
        print(f"  Removidos isentos: {p.removed_isentos} | Removidos JCP: {p.removed_jcp}")
        print(f"  Totais: isentos={p.total_isentos} jcp={p.total_jcp}")
    if s.report_path:
        print(f"Relatório: {s.report_path}")
    print("Abra no programa da Receita e valide Pendências/Totais antes de transmitir.")
