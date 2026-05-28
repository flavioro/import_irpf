from decimal import Decimal
import csv
import xml.etree.ElementTree as ET
from pathlib import Path

from irpf_importer.importers.bens import (
    NS,
    br_money_to_decimal,
    decimal_to_br_money,
    import_bens,
    q,
)


def write_sample_xml(xml: Path) -> None:
    xml.write_text(
        f'''<?xml version="1.0" encoding="UTF-8"?>
<classe xmlns="{NS}">
  <bens totalExercicioAnterior="9.933,00" totalExercicioAtual="1.000,00" totalItens="2" ultimoIndiceGerado="00002">
    <item indice="00001" grupo="02" codigo="01" discriminacao="BEM ORIGINAL 1" valorExercicioAnterior="9.000,00" valorExercicioAtual="1.000,00" pais="105" nomePais="105 - Brasil" registroBem="ABC" registrado="2" unidade="2">
      <participacoesInventario tipoItens="serpro.ppgd.irpf.negocio.bens.ItemPercentualParticipacaoInventario" totalPercentual="0,00" />
      <proprietariosUsufrutuariosBem tipoItens="serpro.ppgd.irpf.negocio.bens.ProprietarioUsufrutuarioBem" />
    </item>
    <item indice="00002" grupo="02" codigo="01" discriminacao="BEM ORIGINAL 2" valorExercicioAnterior="933,00" valorExercicioAtual="0,00" pais="105" nomePais="105 - Brasil" registroBem="DEF" registrado="2" unidade="2">
      <participacoesInventario tipoItens="serpro.ppgd.irpf.negocio.bens.ItemPercentualParticipacaoInventario" totalPercentual="0,00" />
      <proprietariosUsufrutuariosBem tipoItens="serpro.ppgd.irpf.negocio.bens.ProprietarioUsufrutuarioBem" />
    </item>
  </bens>
  <resumo>
    <outrasInformacoes bensDireitosExercicioAnterior="9.933,00" bensDireitosExercicioAtual="1.000,00" />
  </resumo>
</classe>''',
        encoding="utf-8",
    )


def write_bens_csv(csv_path: Path, rows: list[dict[str, str]]) -> None:
    fieldnames = ["acao", "grupo", "codigo", "discriminacao", "valorExercicioAnterior", "valorExercicioAtual"]
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def parse_bens(xml: Path):
    root = ET.parse(xml).getroot()
    bens = root.find(q("bens"))
    assert bens is not None
    return bens


def test_money_roundtrip():
    assert br_money_to_decimal("9.933,00") == Decimal("9933.00")
    assert decimal_to_br_money(Decimal("34933.00")) == "34.933,00"


def test_import_bens_adds_items_and_recalculates_totals(tmp_path: Path):
    xml = tmp_path / "dec.xml"
    csv_path = tmp_path / "bens.csv"
    write_sample_xml(xml)
    write_bens_csv(
        csv_path,
        [
            {
                "acao": "add",
                "grupo": "02",
                "codigo": "01",
                "discriminacao": "BEM NOVO",
                "valorExercicioAnterior": "0,00",
                "valorExercicioAtual": "25.000,00",
            }
        ],
    )

    stats = import_bens(xml, csv_path, mode="add")
    assert stats.added == 1
    assert stats.removed == 0

    bens = parse_bens(xml)
    assert bens.attrib["totalItens"] == "3"
    assert bens.attrib["ultimoIndiceGerado"] == "00003"
    assert bens.attrib["totalExercicioAnterior"] == "9.933,00"
    assert bens.attrib["totalExercicioAtual"] == "26.000,00"

    items = bens.findall(q("item"))
    assert len(items) == 3
    assert items[2].attrib["indice"] == "00003"
    assert items[2].attrib["discriminacao"] == "BEM NOVO"


def test_import_bens_replace_removes_existing_items_and_restarts_index(tmp_path: Path):
    xml = tmp_path / "dec.xml"
    csv_path = tmp_path / "bens.csv"
    write_sample_xml(xml)
    write_bens_csv(
        csv_path,
        [
            {
                "acao": "add",
                "grupo": "07",
                "codigo": "03",
                "discriminacao": "FII FAKE",
                "valorExercicioAnterior": "0,00",
                "valorExercicioAtual": "3.068,78",
            },
            {
                "acao": "add",
                "grupo": "07",
                "codigo": "09",
                "discriminacao": "ETF FAKE",
                "valorExercicioAnterior": "0,00",
                "valorExercicioAtual": "2.365,00",
            },
        ],
    )

    stats = import_bens(xml, csv_path, mode="replace")
    assert stats.added == 2
    assert stats.removed == 2

    bens = parse_bens(xml)
    items = bens.findall(q("item"))
    assert len(items) == 2
    assert [item.attrib["indice"] for item in items] == ["00001", "00002"]
    assert bens.attrib["totalItens"] == "2"
    assert bens.attrib["ultimoIndiceGerado"] == "00002"
    assert bens.attrib["totalExercicioAnterior"] == "0,00"
    assert bens.attrib["totalExercicioAtual"] == "5.433,78"
    assert items[0].attrib["discriminacao"] == "FII FAKE"


def test_import_bens_dry_run_does_not_change_file(tmp_path: Path):
    xml = tmp_path / "dec.xml"
    csv_path = tmp_path / "bens.csv"
    write_sample_xml(xml)
    original = xml.read_text(encoding="utf-8")
    write_bens_csv(
        csv_path,
        [
            {
                "acao": "add",
                "grupo": "02",
                "codigo": "01",
                "discriminacao": "BEM SIMULADO",
                "valorExercicioAnterior": "0,00",
                "valorExercicioAtual": "10.000,00",
            }
        ],
    )

    stats = import_bens(xml, csv_path, mode="dry-run")
    assert stats.dry_run is True
    assert stats.added == 1
    assert stats.removed == 0
    assert stats.total_items == 3
    assert stats.total_exercicio_atual == "11.000,00"
    assert xml.read_text(encoding="utf-8") == original
