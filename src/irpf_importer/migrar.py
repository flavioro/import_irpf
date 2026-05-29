from __future__ import annotations

import json
import shutil
import tempfile
from dataclasses import asdict, dataclass, replace
from datetime import datetime
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from .conf import recalcular_conf
from .clone import BLANK_CPF, format_cpf, only_digits, unformat_cpf
from .importers.bens import ImportStats as BensStats, import_bens
from .importers.proventos import ProventosStats, import_proventos
from .xml_utils import NS, q

ET.register_namespace("", NS)

IDENTIFIER_TAGS = ("identificadorDec", "identificadorDeclaracao", "copiaIdentificador")
RECEIPT_ATTRS = ("numeroReciboDecAnterior", "numReciboDecRetif", "numReciboTransmitido")
TRANSMISSION_ATTRS = ("transmitida", "tpTransmitida", "declaracaoRetificadora")


@dataclass(frozen=True)
class MigrationStats:
    dry_run: bool
    source_xml: Path
    target_xml: Path
    target_conf: Path
    target_cpf: str
    target_name: str
    receipts_cleared: int
    identifiers_updated: int
    cpf_beneficiario_updated: int
    bens: BensStats | None
    proventos: ProventosStats | None
    report_path: Path | None = None


@dataclass(frozen=True)
class MigrationResult:
    stats: MigrationStats


def _read_source_identity(root: ET.Element, source_xml: Path) -> tuple[str, str]:
    for tag in ("identificadorDeclaracao", "identificadorDec", "copiaIdentificador"):
        el = root.find(f".//{q(tag)}")
        if el is not None:
            cpf = only_digits(el.attrib.get("cpf"))
            nome = (el.attrib.get("nome") or "").strip()
            if cpf:
                return cpf, nome
    m = re.search(r"(\d{11})", source_xml.name)
    return (m.group(1) if m else "00000000000", "")


def _target_paths(source_xml: Path, target_dir: Path, target_cpf: str | None) -> tuple[str, Path, Path]:
    cpf_digits = unformat_cpf(target_cpf) if target_cpf else (_read_cpf_from_filename(source_xml) or "00000000000")
    folder = target_dir / cpf_digits
    xml = folder / f"{cpf_digits}-0000000000.xml"
    conf = xml.with_suffix(".conf")
    return cpf_digits, xml, conf


def _read_cpf_from_filename(path: Path) -> str | None:
    m = re.search(r"(\d{11})", path.name)
    return m.group(1) if m else None


def prepare_xml_for_next_year(
    root: ET.Element,
    *,
    target_cpf: str | None = None,
    target_name: str | None = None,
    clear_receipts: bool = True,
) -> tuple[str, str, int, int, int]:
    source_cpf, source_name = _read_source_identity(root, Path("declaracao.xml"))
    cpf_digits = unformat_cpf(target_cpf) if target_cpf else source_cpf
    cpf_fmt = format_cpf(cpf_digits) if cpf_digits and cpf_digits != "00000000000" else (format_cpf(cpf_digits) if len(cpf_digits) == 11 else BLANK_CPF)
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
                        ident.attrib[attr] = "0" if attr == "transmitida" or attr == "declaracaoRetificadora" else ""
                ident.attrib["dataUltimoAcesso"] = now

    if target_cpf:
        for element in root.iter():
            if "cpfBeneficiario" in element.attrib and element.attrib.get("cpfBeneficiario") != cpf_fmt:
                element.attrib["cpfBeneficiario"] = cpf_fmt
                cpf_beneficiario_updated += 1

    return cpf_digits, name, receipts_cleared, identifiers_updated, cpf_beneficiario_updated


def _stats_to_report(stats: MigrationStats) -> dict[str, object]:
    data = asdict(stats)
    for key in ("source_xml", "target_xml", "target_conf", "report_path"):
        if data.get(key) is not None:
            data[key] = str(data[key])
    return data


def migrate_declaration(
    *,
    source_xml: Path,
    target_dir: Path,
    irpf_dir: Path | None = None,
    bens_file: Path | None = None,
    proventos_file: Path | None = None,
    target_cpf: str | None = None,
    target_name: str | None = None,
    clear_receipts: bool = True,
    recalc_conf: bool = True,
    dry_run: bool = False,
    bens_mode: str = "upsert",
    proventos_mode: str = "replace",
    report_path: Path | None = None,
) -> MigrationResult:
    source_xml = Path(source_xml)
    target_dir = Path(target_dir)
    if not source_xml.exists():
        raise FileNotFoundError(source_xml)
    if bens_file is not None and not Path(bens_file).exists():
        raise FileNotFoundError(bens_file)
    if proventos_file is not None and not Path(proventos_file).exists():
        raise FileNotFoundError(proventos_file)
    if recalc_conf and not dry_run:
        if irpf_dir is None:
            raise RuntimeError("--irpf-dir é obrigatório para recalcular o .conf.")
        if not Path(irpf_dir).exists():
            raise FileNotFoundError(irpf_dir)

    inferred_cpf = target_cpf or _read_cpf_from_filename(source_xml)
    cpf_digits, intended_xml, intended_conf = _target_paths(source_xml, target_dir, inferred_cpf)

    def run_pipeline(work_xml: Path, *, write_final: bool) -> tuple[str, str, int, int, int, BensStats | None, ProventosStats | None]:
        tree = ET.parse(source_xml)
        root = tree.getroot()
        final_cpf, final_name, receipts, identifiers, cpf_benef = prepare_xml_for_next_year(
            root,
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
        if intended_xml.parent.exists() and any(intended_xml.parent.iterdir()):
            # Não apaga dados existentes automaticamente; apenas sobrescreve o XML alvo.
            pass
        final_cpf, final_name, receipts, identifiers, cpf_benef, bens_stats, proventos_stats = run_pipeline(intended_xml, write_final=True)

    stats = MigrationStats(
        dry_run=dry_run,
        source_xml=source_xml,
        target_xml=intended_xml,
        target_conf=intended_conf,
        target_cpf=final_cpf,
        target_name=final_name,
        receipts_cleared=receipts,
        identifiers_updated=identifiers,
        cpf_beneficiario_updated=cpf_benef,
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
    print("Migração 2025 -> 2026")
    print(f"XML origem: {s.source_xml}")
    print(f"XML destino: {s.target_xml}")
    print(f"CONF destino: {s.target_conf}")
    print(f"CPF destino: {s.target_cpf}")
    print(f"Nome destino: {s.target_name}")
    print(f"Recibos limpos: {s.receipts_cleared}")
    print(f"Identificadores atualizados: {s.identifiers_updated}")
    print(f"cpfBeneficiario atualizados: {s.cpf_beneficiario_updated}")
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
