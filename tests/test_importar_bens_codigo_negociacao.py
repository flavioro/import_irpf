from __future__ import annotations

import csv
from pathlib import Path
import xml.etree.ElementTree as ET

from irpf_importer.importers.bens import NS, import_bens, q


def write_xml_with_investments(xml: Path) -> None:
    xml.write_text(
        f'''<?xml version="1.0" encoding="UTF-8"?>
<classe xmlns="{NS}">
  <bens totalExercicioAnterior="1.000,00" totalExercicioAtual="2.000,00" totalItens="2" ultimoIndiceGerado="00002">
    <item indice="00001" grupo="03" codigo="01" codigoNegociacao="CMIG4" discriminacao="CMIG4; CIA ENERGETICA DE MINAS GERAIS" niEmpresa="17.155.730/0001-64" registroBem="" valorExercicioAnterior="1.000,00" valorExercicioAtual="2.000,00" pais="105" nomePais="105 - Brasil" registrado="2" unidade="2">
      <participacoesInventario tipoItens="serpro.ppgd.irpf.negocio.bens.ItemPercentualParticipacaoInventario" totalPercentual="0,00" />
      <proprietariosUsufrutuariosBem tipoItens="serpro.ppgd.irpf.negocio.bens.ProprietarioUsufrutuarioBem" />
    </item>
    <item indice="00002" grupo="02" codigo="01" codigoNegociacao="" discriminacao="HONDA 125 FAN" registroBem="00453064914" valorExercicioAnterior="0,00" valorExercicioAtual="5.000,00" pais="105" nomePais="105 - Brasil" registrado="2" unidade="2">
      <participacoesInventario tipoItens="serpro.ppgd.irpf.negocio.bens.ItemPercentualParticipacaoInventario" totalPercentual="0,00" />
      <proprietariosUsufrutuariosBem tipoItens="serpro.ppgd.irpf.negocio.bens.ProprietarioUsufrutuarioBem" />
    </item>
  </bens>
  <resumo>
    <outrasInformacoes bensDireitosExercicioAnterior="1.000,00" bensDireitosExercicioAtual="7.000,00" />
  </resumo>
</classe>''',
        encoding="utf-8",
    )


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fieldnames = [
        "acao",
        "grupo",
        "codigo",
        "codigoNegociacao",
        "registroBem",
        "discriminacao",
        "niEmpresa",
        "valorExercicioAnterior",
        "valorExercicioAtual",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def items_by_codigo(xml: Path) -> dict[str, ET.Element]:
    bens = ET.parse(xml).getroot().find(q("bens"))
    assert bens is not None
    return {item.attrib.get("codigoNegociacao", ""): item for item in bens.findall(q("item"))}


def test_upsert_uses_codigo_negociacao_when_registro_bem_is_empty_in_xml(tmp_path: Path):
    xml = tmp_path / "dec.xml"
    csv_path = tmp_path / "bens.csv"
    write_xml_with_investments(xml)
    write_csv(
        csv_path,
        [
            {
                "acao": "upsert",
                "grupo": "03",
                "codigo": "01",
                "codigoNegociacao": "CMIG4",
                "registroBem": "CMIG4",
                "discriminacao": "CMIG4; CIA ENERGETICA DE MINAS GERAIS",
                "niEmpresa": "17.155.730/0001-64",
                "valorExercicioAnterior": "1.100,00",
                "valorExercicioAtual": "4.200,00",
            }
        ],
    )

    stats = import_bens(xml, csv_path, mode="upsert")

    assert stats.updated == 1
    assert stats.added == 0
    assert stats.total_items == 2
    assert stats.total_exercicio_atual == "9.200,00"
    cmig = items_by_codigo(xml)["CMIG4"]
    assert cmig.attrib["indice"] == "00001"
    assert cmig.attrib["valorExercicioAtual"] == "4.200,00"
    assert cmig.attrib["codigoNegociacao"] == "CMIG4"


def test_dry_run_simulates_upsert_and_does_not_change_file(tmp_path: Path):
    xml = tmp_path / "dec.xml"
    csv_path = tmp_path / "bens.csv"
    write_xml_with_investments(xml)
    original = xml.read_text(encoding="utf-8")
    write_csv(
        csv_path,
        [
            {
                "acao": "upsert",
                "grupo": "03",
                "codigo": "01",
                "codigoNegociacao": "CMIG4",
                "registroBem": "CMIG4",
                "discriminacao": "CMIG4; CIA ENERGETICA DE MINAS GERAIS",
                "niEmpresa": "17.155.730/0001-64",
                "valorExercicioAnterior": "1.100,00",
                "valorExercicioAtual": "4.200,00",
            }
        ],
    )

    stats = import_bens(xml, csv_path, mode="dry-run")

    assert stats.dry_run is True
    assert stats.updated == 1
    assert stats.added == 0
    assert xml.read_text(encoding="utf-8") == original


def test_upsert_consolidates_duplicate_codigo_negociacao_rows_before_update(tmp_path: Path):
    xml = tmp_path / "dec.xml"
    csv_path = tmp_path / "bens.csv"
    write_xml_with_investments(xml)
    write_csv(
        csv_path,
        [
            {
                "acao": "upsert",
                "grupo": "03",
                "codigo": "01",
                "codigoNegociacao": "CMIG4",
                "registroBem": "CMIG4",
                "discriminacao": "CMIG4; corretora A",
                "niEmpresa": "17.155.730/0001-64",
                "valorExercicioAnterior": "100,00",
                "valorExercicioAtual": "1.500,00",
            },
            {
                "acao": "upsert",
                "grupo": "03",
                "codigo": "01",
                "codigoNegociacao": "CMIG4",
                "registroBem": "CMIG4",
                "discriminacao": "CMIG4; corretora B",
                "niEmpresa": "17.155.730/0001-64",
                "valorExercicioAnterior": "200,00",
                "valorExercicioAtual": "2.500,00",
            },
        ],
    )

    stats = import_bens(xml, csv_path, mode="upsert")

    assert stats.consolidated_duplicates == 1
    assert stats.updated == 1
    assert stats.added == 0
    cmig = items_by_codigo(xml)["CMIG4"]
    assert cmig.attrib["valorExercicioAnterior"] == "300,00"
    assert cmig.attrib["valorExercicioAtual"] == "4.000,00"


def test_upsert_skips_ambiguous_codigo_negociacao_instead_of_adding_duplicate(tmp_path: Path):
    xml = tmp_path / "dec.xml"
    csv_path = tmp_path / "bens.csv"
    xml.write_text(
        f'''<?xml version="1.0" encoding="UTF-8"?>
<classe xmlns="{NS}">
  <bens totalExercicioAnterior="0,00" totalExercicioAtual="12.586,40" totalItens="2" ultimoIndiceGerado="00002">
    <item indice="00001" grupo="07" codigo="03" codigoNegociacao="JSRE11" discriminacao="JSRE11, BANCO SAFRA" niEmpresa="13.371.132/0001-71" registroBem="" valorExercicioAnterior="6.293,60" valorExercicioAtual="6.293,60" pais="105" nomePais="105 - Brasil" registrado="2" unidade="2" />
    <item indice="00002" grupo="07" codigo="03" codigoNegociacao="JSRE11" discriminacao="JSRE11 - JS REAL ESTATE" niEmpresa="13.371.132/0001-71" registroBem="" valorExercicioAnterior="0,00" valorExercicioAtual="6.292,80" pais="105" nomePais="105 - Brasil" registrado="2" unidade="2" />
  </bens>
  <resumo><outrasInformacoes bensDireitosExercicioAnterior="0,00" bensDireitosExercicioAtual="12.586,40" /></resumo>
</classe>''',
        encoding="utf-8",
    )
    original = xml.read_text(encoding="utf-8")
    write_csv(
        csv_path,
        [
            {
                "acao": "upsert",
                "grupo": "07",
                "codigo": "03",
                "codigoNegociacao": "JSRE11",
                "registroBem": "JSRE11",
                "discriminacao": "JSRE11 consolidado",
                "niEmpresa": "13.371.132/0001-71",
                "valorExercicioAnterior": "6.293,60",
                "valorExercicioAtual": "6.293,60",
            }
        ],
    )

    stats = import_bens(xml, csv_path, mode="dry-run")

    assert stats.added == 0
    assert stats.updated == 0
    assert stats.ambiguous_keys == 1
    assert stats.skipped_ambiguous == 1
    assert stats.total_items == 2
    assert xml.read_text(encoding="utf-8") == original
