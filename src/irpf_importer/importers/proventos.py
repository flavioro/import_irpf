from __future__ import annotations

import argparse
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
import xml.etree.ElementTree as ET

from ..backup import backup_files
from ..conf import recalcular_conf
from ..io_tables import read_table_rows
from ..money import br_money_to_decimal, decimal_to_br_money
from ..xml_utils import NS, find_required, find_resumo_outras_info, q

SUPPORTED_MODES = ("add", "replace", "dry-run")

DIVIDENDO_EVENTOS = ("dividendo", "rendimento")
JCP_EVENTOS = ("juros sobre capital", "jcp")


def obter_cpf_titular(root: ET.Element) -> str:
    identificador = root.find(f".//{q('identificadorDeclaracao')}")
    if identificador is not None and identificador.attrib.get("cpf"):
        return identificador.attrib["cpf"]
    return "   .   .   -  "


def categorizar_evento(tipo_evento: str) -> str:
    normalized = (tipo_evento or "").strip().lower()
    if any(term in normalized for term in JCP_EVENTOS):
        return "jcp"
    if any(term in normalized for term in DIVIDENDO_EVENTOS):
        return "isento"
    return "ignorado"


def make_rendimento_item(root: ET.Element, row: dict[str, str]) -> ET.Element:
    produto = (row.get("produto") or "").strip()
    tipo_evento = (row.get("tipoEvento") or "").strip()
    valor = decimal_to_br_money(br_money_to_decimal(row.get("valorLiquido")))
    nome_fonte = (row.get("nomeFonte") or "").strip()
    if not nome_fonte:
        nome_fonte = f"{produto} - {tipo_evento}".strip(" -")

    # CSV atual não traz CNPJ da fonte pagadora. Mantemos vazio para teste fake;
    # o IRPF pode apontar pendência até preencher o CNPJ correto na interface.
    cnpj = (row.get("cnpjEmpresa") or row.get("cnpj") or "").strip()

    return ET.Element(
        q("item"),
        {
            "cnpjEmpresa": cnpj,
            "codBem": (row.get("codBem") or "").strip(),
            "cpfAlimentante": "   .   .   -  ",
            "cpfBeneficiario": obter_cpf_titular(root),
            "nomeFonte": nome_fonte,
            "tipoBeneficiario": (row.get("tipoBeneficiario") or "Titular").strip() or "Titular",
            "valor": valor,
            "valor13Salario": "0,00",
        },
    )


def total_children_value(parent: ET.Element) -> Decimal:
    total = Decimal("0.00")
    for item in parent.findall(q("item")):
        total += br_money_to_decimal(item.attrib.get("valor", "0,00"))
    return total


def remove_items(parent: ET.Element) -> int:
    removed = 0
    for item in list(parent.findall(q("item"))):
        parent.remove(item)
        removed += 1
    return removed


def ensure_child(parent: ET.Element, tag: str, tipo_itens: str = "serpro.ppgd.irpf.negocio.rendIsentos.ItemQuadroTransporteDetalhado") -> ET.Element:
    child = parent.find(q(tag))
    if child is None:
        child = ET.SubElement(parent, q(tag), {"tipoItens": tipo_itens, "totais": "0,00"})
    return child


def update_total_by_replacing_target(container: ET.Element, target_attr: str, new_target_total: Decimal) -> str:
    old_target_total = br_money_to_decimal(container.attrib.get(target_attr, "0,00"))
    old_container_total = br_money_to_decimal(container.attrib.get("total", "0,00"))
    new_container_total = old_container_total - old_target_total + new_target_total
    container.attrib[target_attr] = decimal_to_br_money(new_target_total)
    container.attrib["total"] = decimal_to_br_money(new_container_total)
    return decimal_to_br_money(new_container_total)


@dataclass(frozen=True)
class ProventosStats:
    mode: str
    isentos_added: int
    jcp_added: int
    ignored: int
    removed_isentos: int
    removed_jcp: int
    existing_isentos: str
    existing_jcp: str
    csv_isentos: str
    csv_jcp: str
    csv_importavel_total: str
    csv_ignorado_total: str
    total_isentos: str
    total_jcp: str
    total_nao_tributaveis: str
    total_exclusivos: str
    dry_run: bool = False


@dataclass(frozen=True)
class ProventosResult:
    stats: ProventosStats
    xml_backup: Path | None
    conf_backup: Path | None


def import_proventos(xml_path: Path, csv_path: Path, mode: str = "add", write: bool = True) -> ProventosStats:
    mode = mode.strip().lower()
    if mode not in SUPPORTED_MODES:
        raise ValueError(f"Modo inválido: {mode}. Use: {', '.join(SUPPORTED_MODES)}")

    dry_run = mode == "dry-run" or not write
    effective_mode = "add" if mode == "dry-run" else mode

    tree = ET.parse(xml_path)
    root = tree.getroot()

    rend_isentos = find_required(root, "rendIsentos")
    lucro_quadro = ensure_child(rend_isentos, "lucroRecebidoQuadroAuxiliar")

    rend_exclusiva = find_required(root, "rendTributacaoExclusiva")
    jcp_quadro = ensure_child(rend_exclusiva, "jurosCapitalProprioQuadroAuxiliar")

    existing_isentos_decimal = total_children_value(lucro_quadro)
    existing_jcp_decimal = total_children_value(jcp_quadro)

    removed_isentos = 0
    removed_jcp = 0
    if effective_mode == "replace":
        removed_isentos = remove_items(lucro_quadro)
        removed_jcp = remove_items(jcp_quadro)

    isentos_added = 0
    jcp_added = 0
    ignored = 0
    csv_isentos_decimal = Decimal("0.00")
    csv_jcp_decimal = Decimal("0.00")
    csv_ignorado_decimal = Decimal("0.00")

    fieldnames, rows = read_table_rows(csv_path)
    required = {"produto", "tipoEvento", "valorLiquido"}
    missing = required - set(fieldnames)
    if missing:
        raise RuntimeError(f"Arquivo sem colunas obrigatórias: {', '.join(sorted(missing))}")

    for row_number, row in enumerate(rows, start=2):
        produto = (row.get("produto") or "").strip()
        valor = br_money_to_decimal(row.get("valorLiquido"))
        if not produto or valor == Decimal("0.00"):
            ignored += 1
            csv_ignorado_decimal += valor
            continue

        categoria = categorizar_evento(row.get("tipoEvento", ""))
        if categoria == "isento":
            lucro_quadro.append(make_rendimento_item(root, row))
            isentos_added += 1
            csv_isentos_decimal += valor
        elif categoria == "jcp":
            jcp_quadro.append(make_rendimento_item(root, row))
            jcp_added += 1
            csv_jcp_decimal += valor
        else:
            ignored += 1
            csv_ignorado_decimal += valor

    total_isentos_decimal = total_children_value(lucro_quadro)
    total_jcp_decimal = total_children_value(jcp_quadro)

    lucro_quadro.attrib["totais"] = decimal_to_br_money(total_isentos_decimal)
    jcp_quadro.attrib["totais"] = decimal_to_br_money(total_jcp_decimal)

    total_nao_tributaveis = update_total_by_replacing_target(rend_isentos, "lucroRecebido", total_isentos_decimal)
    total_exclusivos = update_total_by_replacing_target(rend_exclusiva, "jurosCapitalProprio", total_jcp_decimal)

    outras = find_resumo_outras_info(root)
    if outras is not None:
        outras.attrib["rendIsentosNaoTributaveis"] = total_nao_tributaveis
        outras.attrib["rendIsentosTributacaoExclusiva"] = total_exclusivos

    stats = ProventosStats(
        mode=mode,
        isentos_added=isentos_added,
        jcp_added=jcp_added,
        ignored=ignored,
        removed_isentos=removed_isentos,
        removed_jcp=removed_jcp,
        existing_isentos=decimal_to_br_money(existing_isentos_decimal),
        existing_jcp=decimal_to_br_money(existing_jcp_decimal),
        csv_isentos=decimal_to_br_money(csv_isentos_decimal),
        csv_jcp=decimal_to_br_money(csv_jcp_decimal),
        csv_importavel_total=decimal_to_br_money(csv_isentos_decimal + csv_jcp_decimal),
        csv_ignorado_total=decimal_to_br_money(csv_ignorado_decimal),
        total_isentos=decimal_to_br_money(total_isentos_decimal),
        total_jcp=decimal_to_br_money(total_jcp_decimal),
        total_nao_tributaveis=total_nao_tributaveis,
        total_exclusivos=total_exclusivos,
        dry_run=dry_run,
    )

    if not dry_run:
        tree.write(xml_path, encoding="utf-8", xml_declaration=True)

    return stats


def run_import(
    irpf_dir: Path,
    xml_path: Path,
    csv_path: Path,
    recalc_conf: bool = True,
    backup_dir: Path | None = None,
    mode: str = "add",
) -> ProventosResult:
    mode = mode.strip().lower()
    if mode not in SUPPORTED_MODES:
        raise ValueError(f"Modo inválido: {mode}. Use: {', '.join(SUPPORTED_MODES)}")
    if not irpf_dir.exists():
        raise FileNotFoundError(irpf_dir)
    if not xml_path.exists():
        raise FileNotFoundError(xml_path)
    if not csv_path.exists():
        raise FileNotFoundError(csv_path)

    dry_run = mode == "dry-run"
    xml_backup = None
    conf_backup = None
    if not dry_run:
        xml_backup, conf_backup = backup_files(xml_path, backup_dir, operation="import_proventos")

    stats = import_proventos(xml_path, csv_path, mode=mode, write=not dry_run)
    if recalc_conf and not dry_run:
        recalcular_conf(irpf_dir, xml_path)
    return ProventosResult(stats=stats, xml_backup=xml_backup, conf_backup=conf_backup)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Importa proventos de CSV para Rendimentos Isentos e Tributação Exclusiva no XML local do IRPF 2026."
    )
    parser.add_argument("--irpf-dir", required=True, help="Pasta de instalação do IRPF, ex.: C:\\Arquivos de Programas RFB\\IRPF2026")
    parser.add_argument("--xml", required=True, help="Caminho do XML da declaração fake/teste.")
    parser.add_argument("--csv", required=True, help="Arquivo CSV/XLSX de proventos com produto,tipoEvento,valorLiquido.")
    parser.add_argument("--backup-dir", default=None, help="Pasta para backups do XML/.conf antes da alteração.")
    parser.add_argument(
        "--mode",
        choices=SUPPORTED_MODES,
        default="add",
        help="add adiciona itens; replace remove proventos atuais desses quadros e importa o CSV; dry-run simula sem alterar XML/.conf.",
    )
    parser.add_argument("--sem-recalcular-conf", action="store_true", help="Não recalcula o .conf. Use apenas para testes internos.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    result = run_import(
        irpf_dir=Path(args.irpf_dir),
        xml_path=Path(args.xml),
        csv_path=Path(args.csv),
        recalc_conf=not args.sem_recalcular_conf,
        backup_dir=Path(args.backup_dir) if args.backup_dir else None,
        mode=args.mode,
    )
    stats = result.stats
    if stats.dry_run:
        print("DRY-RUN: nenhum arquivo foi alterado e o .conf não foi recalculado.")
    print(f"Modo: {stats.mode}")
    print(f"Itens removidos em Rendimentos Isentos: {stats.removed_isentos}")
    print(f"Itens removidos em JCP/Tributação Exclusiva: {stats.removed_jcp}")
    print(f"Itens adicionados em Rendimentos Isentos: {stats.isentos_added}")
    print(f"Itens adicionados em JCP/Tributação Exclusiva: {stats.jcp_added}")
    print(f"Itens ignorados/não suportados: {stats.ignored}")
    print(f"Total existente no XML - Rendimentos Isentos: {stats.existing_isentos}")
    print(f"Total existente no XML - JCP/Tributação Exclusiva: {stats.existing_jcp}")
    print(f"Total vindo do CSV - Rendimentos Isentos: {stats.csv_isentos}")
    print(f"Total vindo do CSV - JCP/Tributação Exclusiva: {stats.csv_jcp}")
    print(f"Total importável vindo do CSV: {stats.csv_importavel_total}")
    print(f"Total ignorado/não suportado vindo do CSV: {stats.csv_ignorado_total}")
    print(f"Total final no XML - lucro/dividendos/rendimentos isentos: {stats.total_isentos}")
    print(f"Total final no XML - JCP: {stats.total_jcp}")
    print(f"Total final no XML - Rendimentos Isentos e Não Tributáveis: {stats.total_nao_tributaveis}")
    print(f"Total final no XML - Tributação Exclusiva: {stats.total_exclusivos}")
    if result.xml_backup:
        print(f"Backup XML: {result.xml_backup}")
    if result.conf_backup:
        print(f"Backup CONF: {result.conf_backup}")
    print("Abra o IRPF e valide a declaração pela interface oficial.")


if __name__ == "__main__":
    main()
