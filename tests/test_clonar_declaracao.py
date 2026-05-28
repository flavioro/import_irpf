from pathlib import Path
import xml.etree.ElementTree as ET

from irpf_importer.clone import clone_declaration, q


def write_sample_xml(path: Path) -> None:
    xml = '''<?xml version="1.0" encoding="UTF-8"?>
<classe xmlns="http://www.receita.fazenda.gov.br/declaracao" classeJava="serpro.ppgd.irpf.negocio.DeclaracaoIRPF" dataHoraSalvamento="01/01/2026 10:00:00" utlimoCPFAutenticado="111.111.111-11">
  <contribuinte email="old@example.com" celular="999" dddCelular="11" dataNascimento="01/01/1970" cep="00000-000" tipoLogradouro="RUA" logradouro="ANTIGA" numero="1" complemento="" bairro="CENTRO" municipio="0001" uf="SP" naturezaOcupacao="01" ocupacaoPrincipal="519" cpfConjuge="111.111.111-11" cpfProcurador="111.111.111-11" tituloEleitor="123"/>
  <dependentes tipoItens="serpro.ppgd.irpf.negocio.dependentes.Dependente"><item cpfDependente="222.222.222-22" nome="FILHO"/></dependentes>
  <alimentandos tipoItens="serpro.ppgd.irpf.negocio.alimentandos.Alimentando"/>
  <rendPJ totalRendRecebPessoaJuridica="1.000,00"><colecaoRendPJTitular totaisRendRecebidoPJ="1.000,00"><item rendRecebidoPJ="1.000,00"/></colecaoRendPJTitular><colecaoRendPJDependente/></rendPJ>
  <rendIsentos lucroRecebido="100,00" total="100,00"><lucroRecebidoQuadroAuxiliar totais="100,00"><item cpfBeneficiario="111.111.111-11" nomeFonte="EMPRESA" valor="100,00"/></lucroRecebidoQuadroAuxiliar></rendIsentos>
  <rendTributacaoExclusiva jurosCapitalProprio="200,00" total="200,00"><jurosCapitalProprioQuadroAuxiliar totais="200,00"><item cpfBeneficiario="111.111.111-11" nomeFonte="EMPRESA" valor="200,00"/></jurosCapitalProprioQuadroAuxiliar></rendTributacaoExclusiva>
  <pagamentos totalDespesasMedicas="300,00" ultimoIndiceGerado="00001"><item valorPago="300,00"/></pagamentos>
  <doacoes totalDeducaoIncentivo="0,0000" ultimoIndiceGerado=""/>
  <bens totalExercicioAnterior="10,00" totalExercicioAtual="20,00" totalItens="1" ultimoIndiceGerado="00001"><item indice="00001" valorExercicioAnterior="10,00" valorExercicioAtual="20,00" cpfBeneficiario="111.111.111-11"/></bens>
  <dividas totalExercicioAnterior="5,00" totalExercicioAtual="6,00" totalPgtoAnual="1,00"><item valor="5,00"/></dividas>
  <resumo><outrasInformacoes bensDireitosExercicioAnterior="10,00" bensDireitosExercicioAtual="20,00" rendIsentosNaoTributaveis="100,00" rendIsentosTributacaoExclusiva="200,00"/><calculoImposto imposto="1,00"><identificadorDec cpf="111.111.111-11" nome="ANTIGO" numReciboTransmitido="999" numeroReciboDecAnterior="888" transmitida="1"/></calculoImposto><identificadorDeclaracao cpf="111.111.111-11" nome="ANTIGO" numReciboTransmitido="999" numeroReciboDecAnterior="888" transmitida="1"/></resumo>
  <rendaVariavel totalImpostoAPagar="10,00"/>
  <fundosInvestimentos totalImpostoDevido="10,00"/>
  <atividadeRural ultimoIndiceGerado="00001"><brasil><identificacaoImovel ultimoIndiceGerado="00001"><item valor="10,00"/></identificacaoImovel></brasil></atividadeRural>
</classe>'''
    path.write_text(xml, encoding="utf-8")


def parse_xml(path: Path) -> ET.Element:
    return ET.parse(path).getroot()


def test_clone_identidade_updates_identity_but_keeps_financial_items(tmp_path: Path):
    source = tmp_path / "source.xml"
    write_sample_xml(source)
    target_dir = tmp_path / "dados"

    result = clone_declaration(
        source_xml=source,
        target_dir=target_dir,
        target_cpf="86320947187",
        target_name="PESSOA TESTE",
        mode="identidade",
        dry_run=False,
        recalc_conf=False,
        email="teste@example.com",
    )

    assert result.stats.target_xml.exists()
    root = parse_xml(result.stats.target_xml)
    identificador = root.find(f".//{q('identificadorDeclaracao')}")
    assert identificador is not None
    assert identificador.attrib["cpf"] == "863.209.471-87"
    assert identificador.attrib["nome"] == "PESSOA TESTE"
    assert identificador.attrib["transmitida"] == "0"
    assert root.find(q("contribuinte")).attrib["email"] == "teste@example.com"
    assert len(root.find(q("bens")).findall(q("item"))) == 1
    assert len(root.find(q("dependentes")).findall(q("item"))) == 0


def test_clone_template_limpo_cleans_financial_sections(tmp_path: Path):
    source = tmp_path / "source.xml"
    write_sample_xml(source)
    result = clone_declaration(
        source_xml=source,
        target_dir=tmp_path / "dados",
        target_cpf="86320947187",
        target_name="PESSOA TESTE",
        mode="template-limpo",
        dry_run=False,
        recalc_conf=False,
    )

    root = parse_xml(result.stats.target_xml)
    assert root.find(q("bens")).attrib["totalItens"] == "0"
    assert root.find(q("bens")).attrib["totalExercicioAtual"] == "0,00"
    assert len(root.find(q("bens")).findall(q("item"))) == 0
    assert root.find(q("rendIsentos")).attrib["total"] == "0,00"
    assert len(root.find(f".//{q('lucroRecebidoQuadroAuxiliar')}").findall(q("item"))) == 0
    assert root.find(q("rendTributacaoExclusiva")).attrib["total"] == "0,00"
    assert len(root.find(q("pagamentos")).findall(q("item"))) == 0
    assert result.stats.cleaned_financial_sections is True
    assert result.stats.removed_items > 0


def test_clone_dry_run_does_not_create_target_file(tmp_path: Path):
    source = tmp_path / "source.xml"
    write_sample_xml(source)
    result = clone_declaration(
        source_xml=source,
        target_dir=tmp_path / "dados",
        target_cpf="86320947187",
        target_name="PESSOA TESTE",
        mode="template-limpo",
        dry_run=True,
        recalc_conf=False,
    )

    assert result.stats.dry_run is True
    assert not result.stats.target_xml.exists()


def test_clone_rejects_invalid_cpf(tmp_path: Path):
    source = tmp_path / "source.xml"
    write_sample_xml(source)
    try:
        clone_declaration(
            source_xml=source,
            target_dir=tmp_path / "dados",
            target_cpf="123",
            target_name="PESSOA TESTE",
            mode="template-limpo",
            dry_run=True,
            recalc_conf=False,
        )
    except ValueError as exc:
        assert "11 dígitos" in str(exc)
    else:
        raise AssertionError("CPF inválido deveria gerar ValueError")
