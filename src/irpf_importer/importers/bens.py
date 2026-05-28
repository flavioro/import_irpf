from __future__ import annotations

import argparse
from copy import deepcopy
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
import xml.etree.ElementTree as ET

from ..backup import backup_files
from ..conf import recalcular_conf
from ..io_tables import read_table_rows
from ..money import br_money_to_decimal, decimal_to_br_money
from ..xml_utils import NS, clear_children, find_required, find_resumo_outras_info, q

SUPPORTED_MODES = ("add", "replace", "upsert", "dry-run")


def next_index(bens: ET.Element) -> str:
    indices: list[int] = []
    for item in bens.findall(q("item")):
        raw = item.attrib.get("indice", "0")
        try:
            indices.append(int(raw))
        except ValueError:
            continue
    return f"{(max(indices) + 1) if indices else 1:05d}"


def make_item_from_template(bens: ET.Element) -> ET.Element:
    existing = bens.find(q("item"))
    if existing is not None:
        item = deepcopy(existing)
        participacoes = item.find(q("participacoesInventario"))
        if participacoes is not None:
            participacoes.attrib["totalPercentual"] = "0,00"
            clear_children(participacoes)
        proprietarios = item.find(q("proprietariosUsufrutuariosBem"))
        if proprietarios is not None:
            clear_children(proprietarios)
        return item

    item = ET.Element(q("item"))
    ET.SubElement(
        item,
        q("participacoesInventario"),
        {
            "tipoItens": "serpro.ppgd.irpf.negocio.bens.ItemPercentualParticipacaoInventario",
            "totalPercentual": "0,00",
        },
    )
    ET.SubElement(
        item,
        q("proprietariosUsufrutuariosBem"),
        {"tipoItens": "serpro.ppgd.irpf.negocio.bens.ProprietarioUsufrutuarioBem"},
    )
    return item


BEM_DEFAULTS = {
    "agencia": "",
    "areaTotal": "0,0",
    "atualizadoValorBem": "",
    "bairro": "",
    "banco": "000",
    "cep": "",
    "cidade": "",
    "codigo": "",
    "codigoAltcoin": "",
    "codigoNegociacao": "",
    "codigoStablecoin": "",
    "complemento": "",
    "conta": "",
    "cpfBeneficiario": "   .   .   -  ",
    "dataAquisicao": "  /  /    ",
    "discriminacao": "",
    "dvConta": "",
    "grupo": "",
    "impostoPagoExterior": "0,00",
    "impostoPagoExteriorIRRF": "0,00",
    "indicadorAutoCustodiante": "",
    "indicadorBemComUsufruto": "",
    "indicadorBemInventariar": "",
    "indicadorContaPagamento": "0",
    "indicadorProprietarioUsufrutuario": "",
    "indicadorReclassificar": "0",
    "indice": "00000",
    "indiceAnterior": "",
    "logradouro": "",
    "lucroPrejuizo": "0,00",
    "matricula": "",
    "municipio": "0000",
    "negociadoBolsa": "0",
    "niEmpresa": "",
    "nomeCartorio": "",
    "nomeMunicipio": "",
    "nomePais": "105 - Brasil",
    "numero": "",
    "operacao": "",
    "pais": "105",
    "registrado": "2",
    "registroBem": "",
    "tipo": "",
    "uf": "",
    "unidade": "2",
    "valorExercicioAnterior": "0,00",
    "valorExercicioAtual": "0,00",
    "valorRecebido": "0,00",
}

CSV_FIELDS = [field for field in BEM_DEFAULTS if field not in {"indice", "indiceAnterior"}]
MONEY_FIELDS = ("valorExercicioAnterior", "valorExercicioAtual", "valorRecebido")


@dataclass(frozen=True)
class ImportStats:
    mode: str
    added: int
    removed: int
    updated: int
    total_items: int
    total_exercicio_anterior: str
    total_exercicio_atual: str
    dry_run: bool = False
    consolidated_duplicates: int = 0
    ambiguous_keys: int = 0


@dataclass(frozen=True)
class ImportResult:
    stats: ImportStats
    xml_backup: Path | None
    conf_backup: Path | None

    @property
    def added(self) -> int:
        return self.stats.added


def _norm(value: str | None) -> str:
    return " ".join((value or "").strip().upper().split())


def _row_value(row: dict[str, str], field: str) -> str:
    return (row.get(field) or "").strip()


def _looks_like_real_registro_bem(value: str) -> bool:
    """Evita usar ticker/código interno como se fosse registro real do IRPF."""
    raw = value.strip()
    compact = raw.replace(".", "").replace("-", "").replace("/", "").replace(" ", "")
    digits = "".join(ch for ch in compact if ch.isdigit())
    return len(digits) >= 6 and len(digits) >= len(compact) - 1


def bem_key_from_row(row: dict[str, str]) -> str:
    grupo = _row_value(row, "grupo")
    codigo = _row_value(row, "codigo")
    codigo_negociacao = _norm(_row_value(row, "codigoNegociacao"))
    if codigo_negociacao:
        return f"negociacao:{grupo}:{codigo}:{codigo_negociacao}"

    registro = _row_value(row, "registroBem")
    if registro and _looks_like_real_registro_bem(registro):
        return f"registro:{grupo}:{codigo}:{_norm(registro)}"

    ni_empresa = _norm(_row_value(row, "niEmpresa"))
    if ni_empresa:
        return f"empresa:{grupo}:{codigo}:{ni_empresa}"

    discriminacao = _norm(_row_value(row, "discriminacao"))
    return f"natural:{grupo}:{codigo}:{discriminacao}"


def bem_key_from_item(item: ET.Element) -> str:
    grupo = (item.attrib.get("grupo") or "").strip()
    codigo = (item.attrib.get("codigo") or "").strip()
    codigo_negociacao = _norm(item.attrib.get("codigoNegociacao"))
    if codigo_negociacao:
        return f"negociacao:{grupo}:{codigo}:{codigo_negociacao}"

    registro = (item.attrib.get("registroBem") or "").strip()
    if registro and _looks_like_real_registro_bem(registro):
        return f"registro:{grupo}:{codigo}:{_norm(registro)}"

    ni_empresa = _norm(item.attrib.get("niEmpresa"))
    if ni_empresa:
        return f"empresa:{grupo}:{codigo}:{ni_empresa}"

    discriminacao = _norm(item.attrib.get("discriminacao"))
    return f"natural:{grupo}:{codigo}:{discriminacao}"


def _merge_duplicate_rows(base: dict[str, str], incoming: dict[str, str]) -> dict[str, str]:
    merged = dict(base)
    for field in MONEY_FIELDS:
        total = br_money_to_decimal(merged.get(field, "0,00")) + br_money_to_decimal(incoming.get(field, "0,00"))
        merged[field] = decimal_to_br_money(total)

    for field in ("observacao", "instituicao", "conta", "discriminacao"):
        a = (merged.get(field) or "").strip()
        b = (incoming.get(field) or "").strip()
        if b and b not in a:
            merged[field] = f"{a} | {b}" if a else b
    return merged


def consolidate_rows_for_upsert(rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], int]:
    ordered: list[dict[str, str]] = []
    index_by_key: dict[str, int] = {}
    duplicates = 0
    for row in rows:
        key = bem_key_from_row(row)
        if key in index_by_key:
            ordered[index_by_key[key]] = _merge_duplicate_rows(ordered[index_by_key[key]], row)
            duplicates += 1
        else:
            index_by_key[key] = len(ordered)
            ordered.append(dict(row))
    return ordered, duplicates


def apply_bem_row_to_item(item: ET.Element, row: dict[str, str], indice: str, *, reset: bool) -> None:
    if reset:
        item.attrib.clear()
        item.attrib.update(BEM_DEFAULTS)
    item.attrib["indice"] = indice

    for field in CSV_FIELDS:
        value = (row.get(field) or "").strip()
        if value:
            item.attrib[field] = value

    for money_field in MONEY_FIELDS:
        if money_field in item.attrib:
            item.attrib[money_field] = decimal_to_br_money(br_money_to_decimal(item.attrib[money_field]))


# Compatibilidade com testes/código antigo.
def normalize_new_bem_item(item: ET.Element, row: dict[str, str], indice: str) -> None:
    apply_bem_row_to_item(item, row, indice, reset=True)


def recalc_bens_totals(root: ET.Element) -> ImportStats:
    bens = find_required(root, "bens")
    items = bens.findall(q("item"))
    total_anterior = Decimal("0.00")
    total_atual = Decimal("0.00")
    max_indice = 0

    for item in items:
        total_anterior += br_money_to_decimal(item.attrib.get("valorExercicioAnterior", "0,00"))
        total_atual += br_money_to_decimal(item.attrib.get("valorExercicioAtual", "0,00"))
        try:
            max_indice = max(max_indice, int(item.attrib.get("indice", "0")))
        except ValueError:
            pass

    total_anterior_fmt = decimal_to_br_money(total_anterior)
    total_atual_fmt = decimal_to_br_money(total_atual)

    bens.attrib["totalItens"] = str(len(items))
    bens.attrib["ultimoIndiceGerado"] = f"{max_indice:05d}" if max_indice else ""
    bens.attrib["totalExercicioAnterior"] = total_anterior_fmt
    bens.attrib["totalExercicioAtual"] = total_atual_fmt

    outras = find_resumo_outras_info(root)
    if outras is not None:
        outras.attrib["bensDireitosExercicioAnterior"] = total_anterior_fmt
        outras.attrib["bensDireitosExercicioAtual"] = total_atual_fmt

    return ImportStats(
        mode="add",
        added=0,
        removed=0,
        updated=0,
        total_items=len(items),
        total_exercicio_anterior=total_anterior_fmt,
        total_exercicio_atual=total_atual_fmt,
    )


def remove_all_bens_items(bens: ET.Element) -> int:
    removed = 0
    for item in list(bens.findall(q("item"))):
        bens.remove(item)
        removed += 1
    return removed


def validate_bens_row(row: dict[str, str], row_number: int) -> None:
    for field in ("grupo", "codigo", "discriminacao"):
        if not (row.get(field) or "").strip():
            raise RuntimeError(f"Linha {row_number}: campo obrigatório ausente: {field}")
    for field in MONEY_FIELDS:
        if field in row and (row.get(field) or "").strip():
            br_money_to_decimal(row.get(field))


def _build_existing_index(bens: ET.Element) -> tuple[dict[str, ET.Element], int]:
    existing_by_key: dict[str, ET.Element] = {}
    ambiguous_keys = 0
    duplicated: set[str] = set()
    for item in bens.findall(q("item")):
        key = bem_key_from_item(item)
        if key in existing_by_key:
            ambiguous_keys += 1
            duplicated.add(key)
            existing_by_key.pop(key, None)
        elif key not in duplicated:
            existing_by_key[key] = item
    return existing_by_key, ambiguous_keys


def import_bens(xml_path: Path, csv_path: Path, mode: str = "add", write: bool = True) -> ImportStats:
    mode = mode.strip().lower()
    if mode not in SUPPORTED_MODES:
        raise ValueError(f"Modo inválido: {mode}. Use: {', '.join(SUPPORTED_MODES)}")

    dry_run = mode == "dry-run" or not write
    # O dry-run é pensado como simulação segura antes do upsert real.
    effective_mode = "upsert" if mode == "dry-run" else mode

    tree = ET.parse(xml_path)
    root = tree.getroot()
    bens = find_required(root, "bens")
    added = 0
    removed = 0
    updated = 0

    if effective_mode == "replace":
        removed = remove_all_bens_items(bens)

    fieldnames, rows = read_table_rows(csv_path)
    if not fieldnames:
        raise RuntimeError("Arquivo sem cabeçalho.")

    consolidated_duplicates = 0
    if effective_mode == "upsert":
        rows, consolidated_duplicates = consolidate_rows_for_upsert(rows)

    existing_by_key, ambiguous_keys = _build_existing_index(bens)

    for row_number, row in enumerate(rows, start=2):
        acao = (row.get("acao") or ("upsert" if effective_mode == "upsert" else "add")).strip().lower()
        if not acao or acao == "skip":
            continue
        if acao not in {"add", "upsert", "delete"}:
            raise RuntimeError(f"Linha {row_number}: ação não suportada: {acao}")

        validate_bens_row(row, row_number)
        key = bem_key_from_row(row)

        if acao == "delete":
            existing = existing_by_key.get(key)
            if existing is not None:
                bens.remove(existing)
                removed += 1
                existing_by_key.pop(key, None)
            continue

        if effective_mode == "upsert" or acao == "upsert":
            existing = existing_by_key.get(key)
            if existing is not None:
                indice = existing.attrib.get("indice") or next_index(bens)
                old_key = bem_key_from_item(existing)
                apply_bem_row_to_item(existing, row, indice, reset=False)
                existing_by_key.pop(old_key, None)
                existing_by_key[bem_key_from_item(existing)] = existing
                updated += 1
                continue

        if effective_mode not in {"add", "replace", "upsert"}:
            raise RuntimeError(f"Modo efetivo não suportado: {effective_mode}")

        indice = next_index(bens)
        item = make_item_from_template(bens)
        apply_bem_row_to_item(item, row, indice, reset=True)
        bens.append(item)
        existing_by_key[bem_key_from_item(item)] = item
        added += 1

    totals = recalc_bens_totals(root)
    stats = ImportStats(
        mode=mode,
        added=added,
        removed=removed,
        updated=updated,
        total_items=totals.total_items,
        total_exercicio_anterior=totals.total_exercicio_anterior,
        total_exercicio_atual=totals.total_exercicio_atual,
        dry_run=dry_run,
        consolidated_duplicates=consolidated_duplicates,
        ambiguous_keys=ambiguous_keys,
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
) -> ImportResult:
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
        xml_backup, conf_backup = backup_files(xml_path, backup_dir, operation="import_bens")

    stats = import_bens(xml_path, csv_path, mode=mode, write=not dry_run)
    if recalc_conf and not dry_run:
        recalcular_conf(irpf_dir, xml_path)
    return ImportResult(stats=stats, xml_backup=xml_backup, conf_backup=conf_backup)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Importa Bens e Direitos de CSV/XLSX para XML local do IRPF 2026.")
    parser.add_argument("--irpf-dir", required=True, help="Pasta de instalação do IRPF, ex.: C:\\Arquivos de Programas RFB\\IRPF2026")
    parser.add_argument("--xml", required=True, help="Caminho do XML da declaração fake/teste.")
    parser.add_argument("--csv", required=True, help="Arquivo CSV/XLSX com bens a importar.")
    parser.add_argument("--backup-dir", default=None, help="Pasta para backups do XML/.conf antes da alteração.")
    parser.add_argument(
        "--mode",
        choices=SUPPORTED_MODES,
        default="dry-run",
        help="add adiciona; replace remove todos e importa; upsert atualiza por codigoNegociacao/registro real/chave natural; dry-run simula upsert sem alterar XML/.conf.",
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
    print(f"Itens removidos em Bens e Direitos: {stats.removed}")
    print(f"Itens adicionados em Bens e Direitos: {stats.added}")
    print(f"Itens atualizados em Bens e Direitos: {stats.updated}")
    print(f"Duplicados consolidados na entrada: {stats.consolidated_duplicates}")
    print(f"Chaves ambíguas ignoradas no XML: {stats.ambiguous_keys}")
    print(f"Total de itens final: {stats.total_items}")
    print(f"Total exercício anterior: {stats.total_exercicio_anterior}")
    print(f"Total exercício atual: {stats.total_exercicio_atual}")
    if result.xml_backup:
        print(f"Backup XML: {result.xml_backup}")
    if result.conf_backup:
        print(f"Backup CONF: {result.conf_backup}")
    print("Abra o IRPF e valide a declaração pela interface oficial.")


if __name__ == "__main__":
    main()
