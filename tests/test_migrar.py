from __future__ import annotations

import csv
from pathlib import Path
import xml.etree.ElementTree as ET

from irpf_importer.migrar import migrate_declaration, prepare_xml_for_next_year
from irpf_importer.xml_utils import NS, q


def write_source_xml(path: Path) -> None:
    path.write_text(
        f'''<?xml version="1.0" encoding="UTF-8"?>
<classe xmlns="{NS}" dataHoraSalvamento="01/01/2025 10:00:00" utlimoCPFAutenticado="215.855.874-00">
  <contribuinte logradouro="RUA ANTIGA" bairro="CENTRO" cep="13000000" municipio="6591" email="real@example.com" telefone="11112222" celular="999998888" tituloEleitor="1234567890123" dataNascimento="01/01/1980" />
  <identificadorDec cpf="215.855.874-00" nome="CONTRIBUINTE BASE" numeroReciboDecAnterior="123456789012" numReciboDecRetif="999" numReciboTransmitido="888" transmitida="1" declaracaoRetificadora="1" />
  <identificadorDeclaracao cpf="215.855.874-00" nome="CONTRIBUINTE BASE" numeroReciboDecAnterior="123456789012" numReciboDecRetif="999" numReciboTransmitido="888" />
  <copiaIdentificador cpf="215.855.874-00" nome="CONTRIBUINTE BASE" numeroReciboDecAnterior="123456789012" numReciboDecRetif="999" numReciboTransmitido="888" />
  <bens totalExercicioAnterior="1.000,00" totalExercicioAtual="2.000,00" totalItens="1" ultimoIndiceGerado="00001">
    <item indice="00001" grupo="03" codigo="01" codigoNegociacao="CMIG4" discriminacao="CMIG4 antigo" niEmpresa="17.155.730/0001-64" registroBem="" cpfBeneficiario="215.855.874-00" valorExercicioAnterior="1.000,00" valorExercicioAtual="2.000,00" pais="105" nomePais="105 - Brasil" registrado="2" unidade="2">
      <participacoesInventario tipoItens="serpro.ppgd.irpf.negocio.bens.ItemPercentualParticipacaoInventario" totalPercentual="0,00" />
      <proprietariosUsufrutuariosBem tipoItens="serpro.ppgd.irpf.negocio.bens.ProprietarioUsufrutuarioBem" />
    </item>
  </bens>
  <rendIsentos lucroRecebido="0,00" poupanca="0,00" outros="0,00" total="0,00"><lucroRecebidoQuadroAuxiliar tipoItens="serpro.ppgd.irpf.rendIsentos.ItemQuadroTransporteDetalhado" totais="0,00" /></rendIsentos>
  <rendTributacaoExclusiva jurosCapitalProprio="0,00" rendAplicacoes="0,00" total="0,00"><jurosCapitalProprioQuadroAuxiliar tipoItens="serpro.ppgd.irpf.rendIsentos.ItemQuadroTransporteDetalhado" totais="0,00" /></rendTributacaoExclusiva>
  <resumo><outrasInformacoes bensDireitosExercicioAnterior="1.000,00" bensDireitosExercicioAtual="2.000,00" rendIsentosNaoTributaveis="0,00" rendIsentosTributacaoExclusiva="0,00" /></resumo>
</classe>''',
        encoding="utf-8",
    )


def write_bens_csv(path: Path) -> None:
    fieldnames = ["acao", "grupo", "codigo", "codigoNegociacao", "registroBem", "discriminacao", "niEmpresa", "valorExercicioAnterior", "valorExercicioAtual"]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow({"acao": "upsert", "grupo": "03", "codigo": "01", "codigoNegociacao": "CMIG4", "registroBem": "CMIG4", "discriminacao": "CMIG4 atualizado", "niEmpresa": "17.155.730/0001-64", "valorExercicioAnterior": "1.100,00", "valorExercicioAtual": "4.200,00"})
        writer.writerow({"acao": "upsert", "grupo": "03", "codigo": "01", "codigoNegociacao": "VALE3", "registroBem": "VALE3", "discriminacao": "VALE3 novo", "niEmpresa": "33.592.510/0001-54", "valorExercicioAnterior": "0,00", "valorExercicioAtual": "6.000,00"})


def test_prepare_xml_for_next_year_preserves_receipts_by_default(tmp_path: Path):
    xml = tmp_path / "21585587400-0000000000.xml"
    write_source_xml(xml)
    root = ET.parse(xml).getroot()

    cpf, name, receipts, identifiers, cpf_benef = prepare_xml_for_next_year(root)

    assert cpf == "21585587400"
    assert name == "CONTRIBUINTE BASE"
    assert receipts == 0
    assert identifiers == 0
    assert cpf_benef == 0
    for tag in ("identificadorDec", "identificadorDeclaracao", "copiaIdentificador"):
        ident = root.find(q(tag))
        assert ident is not None
        assert ident.attrib["cpf"] == "215.855.874-00"
        assert ident.attrib["numeroReciboDecAnterior"] == "123456789012"
        assert ident.attrib["numReciboDecRetif"] == "999"
        assert ident.attrib["numReciboTransmitido"] == "888"


def test_prepare_xml_for_next_year_clears_receipts_when_requested(tmp_path: Path):
    xml = tmp_path / "21585587400-0000000000.xml"
    write_source_xml(xml)
    root = ET.parse(xml).getroot()

    cpf, name, receipts, identifiers, cpf_benef = prepare_xml_for_next_year(root, clear_receipts=True)

    assert cpf == "21585587400"
    assert name == "CONTRIBUINTE BASE"
    assert receipts == 9
    assert identifiers == 0
    assert cpf_benef == 0
    for tag in ("identificadorDec", "identificadorDeclaracao", "copiaIdentificador"):
        ident = root.find(q(tag))
        assert ident is not None
        assert ident.attrib["numeroReciboDecAnterior"] == ""
        assert ident.attrib["numReciboDecRetif"] == ""
        assert ident.attrib["numReciboTransmitido"] == ""


def test_migrate_declaration_updates_bens_and_does_not_modify_source(tmp_path: Path):
    source = tmp_path / "21585587400-0000000000.xml"
    bens = tmp_path / "bens.csv"
    target_dir = tmp_path / "saida"
    write_source_xml(source)
    write_bens_csv(bens)
    original = source.read_text(encoding="utf-8")

    result = migrate_declaration(
        source_xml=source,
        target_dir=target_dir,
        bens_file=bens,
        recalc_conf=False,
    )

    assert source.read_text(encoding="utf-8") == original
    assert result.stats.dry_run is False
    assert result.stats.bens is not None
    assert result.stats.bens.updated == 1
    assert result.stats.bens.added == 1
    assert result.stats.receipts_cleared == 0
    assert result.stats.target_xml.exists()
    assert result.stats.target_xml.name == "21585587400-0000000000.xml"
    assert result.stats.target_xml.with_suffix(".conf.pending").exists()

    root = ET.parse(result.stats.target_xml).getroot()
    bens_node = root.find(q("bens"))
    assert bens_node is not None
    assert bens_node.attrib["totalItens"] == "2"
    assert bens_node.attrib["totalExercicioAtual"] == "10.200,00"


def test_migrate_declaration_dry_run_does_not_write_target(tmp_path: Path):
    source = tmp_path / "21585587400-0000000000.xml"
    bens = tmp_path / "bens.csv"
    target_dir = tmp_path / "saida"
    write_source_xml(source)
    write_bens_csv(bens)

    result = migrate_declaration(
        source_xml=source,
        target_dir=target_dir,
        bens_file=bens,
        recalc_conf=False,
        dry_run=True,
    )

    assert result.stats.dry_run is True
    assert result.stats.bens is not None
    assert result.stats.bens.updated == 1
    assert result.stats.bens.added == 1
    assert not result.stats.target_xml.exists()


def write_base_2026_xml(path: Path) -> None:
    path.write_text(
        f'''<?xml version="1.0" encoding="UTF-8"?>
<classe xmlns="{NS}" classeJava="serpro.ppgd.irpf.negocio.DeclaracaoIRPF" dataHoraSalvamento="01/01/2026 10:00:00">
  <identificadorDec cpf="174.216.978-37" nome="BASE 2026" numeroReciboDecAnterior="ABC" />
  <contribuinte email="base2026@example.com" />
  <bens totalExercicioAnterior="2.000,00" totalExercicioAtual="0,00" totalItens="1" ultimoIndiceGerado="00001">
    <item indice="00001" grupo="03" codigo="01" codigoNegociacao="CMIG4" discriminacao="CMIG4 base 2026" niEmpresa="17.155.730/0001-64" registroBem="" cpfBeneficiario="174.216.978-37" valorExercicioAnterior="2.000,00" valorExercicioAtual="0,00" pais="105" nomePais="105 - Brasil" registrado="2" unidade="2">
      <participacoesInventario tipoItens="serpro.ppgd.irpf.negocio.bens.ItemPercentualParticipacaoInventario" totalPercentual="0,00" />
      <proprietariosUsufrutuariosBem tipoItens="serpro.ppgd.irpf.negocio.bens.ProprietarioUsufrutuarioBem" />
    </item>
  </bens>
  <rendIsentos total="0,00"><lucroRecebidoQuadroAuxiliar tipoItens="serpro.ppgd.irpf.negocio.rendIsentos.ItemQuadroTransporteDetalhado" totais="0,00" /></rendIsentos>
  <rendTributacaoExclusiva total="0,00"><jurosCapitalProprioQuadroAuxiliar tipoItens="serpro.ppgd.irpf.negocio.rendIsentos.ItemQuadroTransporteDetalhado" totais="0,00" /></rendTributacaoExclusiva>
  <resumo><outrasInformacoes bensDireitosExercicioAnterior="2.000,00" bensDireitosExercicioAtual="0,00" /></resumo>
</classe>''',
        encoding="utf-8",
    )


def write_reference_2025_xml(path: Path) -> None:
    path.write_text(
        f'''<?xml version="1.0" encoding="UTF-8"?>
<classe xmlns="{NS}" classeJava="serpro.ppgd.irpf.DeclaracaoIRPF" dataHoraSalvamento="01/01/2025 10:00:00">
  <identificadorDec cpf="174.216.978-37" nome="REFERENCIA 2025" />
  <bens totalExercicioAnterior="1.000,00" totalExercicioAtual="2.000,00" totalItens="1" ultimoIndiceGerado="00001">
    <item indice="00001" grupo="03" codigo="01" codigoNegociacao="CMIG4" discriminacao="CMIG4 referencia 2025" valorExercicioAnterior="1.000,00" valorExercicioAtual="2.000,00">
      <participacoesInventario tipoItens="serpro.ppgd.irpf.bens.ItemPercentualParticipacaoInventario" totalPercentual="0,00" />
    </item>
  </bens>
</classe>''',
        encoding="utf-8",
    )


def test_migrate_uses_2026_base_not_2025_reference(tmp_path: Path):
    base_2026 = tmp_path / "00000000000-0000000000.xml"
    ref_2025 = tmp_path / "00000000000-1839317427.xml"
    bens = tmp_path / "bens.csv"
    target_dir = tmp_path / "saida"
    write_base_2026_xml(base_2026)
    write_reference_2025_xml(ref_2025)
    write_bens_csv(bens)

    result = migrate_declaration(
        base_xml_2026=base_2026,
        referencia_xml_2025=ref_2025,
        target_dir=target_dir,
        bens_file=bens,
        recalc_conf=False,
    )

    assert result.stats.reference.classe_base_2026 == "serpro.ppgd.irpf.negocio.DeclaracaoIRPF"
    assert result.stats.reference.classe_referencia == "serpro.ppgd.irpf.DeclaracaoIRPF"
    assert result.stats.reference.tipo_itens_base_prefix == "serpro.ppgd.irpf.negocio"
    assert result.stats.reference.tipo_itens_referencia_prefix == "serpro.ppgd.irpf"

    output = result.stats.target_xml.read_text(encoding="utf-8")
    assert "serpro.ppgd.irpf.negocio.DeclaracaoIRPF" in output
    assert "serpro.ppgd.irpf.negocio.bens.ItemPercentualParticipacaoInventario" in output
    assert "serpro.ppgd.irpf.DeclaracaoIRPF" not in output
    assert 'numeroReciboDecAnterior="ABC"' in output


def test_migrate_can_clear_receipts_when_explicitly_requested(tmp_path: Path):
    base_2026 = tmp_path / "00000000000-0000000000.xml"
    bens = tmp_path / "bens.csv"
    target_dir = tmp_path / "saida"
    write_base_2026_xml(base_2026)
    write_bens_csv(bens)

    result = migrate_declaration(
        base_xml_2026=base_2026,
        target_dir=target_dir,
        bens_file=bens,
        recalc_conf=False,
        clear_receipts=True,
    )

    assert result.stats.receipts_cleared == 1
    output = result.stats.target_xml.read_text(encoding="utf-8")
    assert 'numeroReciboDecAnterior="ABC"' not in output
    assert 'numeroReciboDecAnterior=""' in output
