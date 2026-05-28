from pathlib import Path
import xml.etree.ElementTree as ET

from irpf_importer.importers.proventos import import_proventos, q


def write_minimal_xml(path: Path) -> None:
    xml = '''<?xml version="1.0" encoding="UTF-8"?>
<classe xmlns="http://www.receita.fazenda.gov.br/declaracao">
  <rendIsentos lucroRecebido="100,00" total="100,00" totalInformado="0,00" totalTransportado="0,00">
    <lucroRecebidoQuadroAuxiliar tipoItens="serpro.ppgd.irpf.negocio.rendIsentos.ItemQuadroTransporteDetalhado" totais="100,00">
      <item cnpjEmpresa="111" codBem="" cpfAlimentante="   .   .   -  " cpfBeneficiario="111.111.111-11" nomeFonte="Antigo" tipoBeneficiario="Titular" valor="100,00" valor13Salario="0,00" />
    </lucroRecebidoQuadroAuxiliar>
  </rendIsentos>
  <rendTributacaoExclusiva jurosCapitalProprio="200,00" total="200,00">
    <jurosCapitalProprioQuadroAuxiliar tipoItens="serpro.ppgd.irpf.negocio.rendIsentos.ItemQuadroTransporteDetalhado" totais="200,00">
      <item cnpjEmpresa="222" codBem="" cpfAlimentante="   .   .   -  " cpfBeneficiario="111.111.111-11" nomeFonte="JCP Antigo" tipoBeneficiario="Titular" valor="200,00" valor13Salario="0,00" />
    </jurosCapitalProprioQuadroAuxiliar>
  </rendTributacaoExclusiva>
  <resumo>
    <outrasInformacoes rendIsentosNaoTributaveis="100,00" rendIsentosTributacaoExclusiva="200,00" />
    <identificadorDeclaracao cpf="863.209.471-87" />
  </resumo>
</classe>
'''
    path.write_text(xml, encoding="utf-8")


def write_csv(path: Path) -> None:
    path.write_text(
        "produto,tipoEvento,valorLiquido,observacao\n"
        "ABC3,Dividendo,10,00,teste\n"  # malformed on purpose? no; comma in value breaks. keep semicolon? rewrite below
        ,
        encoding="utf-8",
    )


def write_csv_ok(path: Path) -> None:
    path.write_text(
        'produto,tipoEvento,valorLiquido,observacao\n'
        'ABC3,Dividendo,"10,00",teste\n'
        'FII11,Rendimento,"20,50",teste\n'
        'XYZ4,Juros Sobre Capital Próprio,"30,25",teste\n'
        'ITUB4,Reembolso,"5,00",teste\n',
        encoding="utf-8",
    )


def test_replace_proventos_remove_antigos_e_recalcula_totais(tmp_path: Path) -> None:
    xml = tmp_path / "decl.xml"
    csv = tmp_path / "prov.csv"
    write_minimal_xml(xml)
    write_csv_ok(csv)

    stats = import_proventos(xml, csv, mode="replace")

    assert stats.removed_isentos == 1
    assert stats.removed_jcp == 1
    assert stats.isentos_added == 2
    assert stats.jcp_added == 1
    assert stats.ignored == 1
    assert stats.existing_isentos == "100,00"
    assert stats.existing_jcp == "200,00"
    assert stats.csv_isentos == "30,50"
    assert stats.csv_jcp == "30,25"
    assert stats.csv_importavel_total == "60,75"
    assert stats.csv_ignorado_total == "5,00"
    assert stats.total_isentos == "30,50"
    assert stats.total_jcp == "30,25"
    assert stats.total_nao_tributaveis == "30,50"
    assert stats.total_exclusivos == "30,25"

    root = ET.parse(xml).getroot()
    lucro = root.find(f".//{q('lucroRecebidoQuadroAuxiliar')}")
    jcp = root.find(f".//{q('jurosCapitalProprioQuadroAuxiliar')}")
    assert lucro is not None and len(lucro.findall(q("item"))) == 2
    assert jcp is not None and len(jcp.findall(q("item"))) == 1


def test_add_proventos_preserva_antigos(tmp_path: Path) -> None:
    xml = tmp_path / "decl.xml"
    csv = tmp_path / "prov.csv"
    write_minimal_xml(xml)
    write_csv_ok(csv)

    stats = import_proventos(xml, csv, mode="add")

    assert stats.removed_isentos == 0
    assert stats.removed_jcp == 0
    assert stats.existing_isentos == "100,00"
    assert stats.existing_jcp == "200,00"
    assert stats.csv_importavel_total == "60,75"
    assert stats.csv_ignorado_total == "5,00"
    assert stats.total_isentos == "130,50"
    assert stats.total_jcp == "230,25"

    root = ET.parse(xml).getroot()
    lucro = root.find(f".//{q('lucroRecebidoQuadroAuxiliar')}")
    jcp = root.find(f".//{q('jurosCapitalProprioQuadroAuxiliar')}")
    assert lucro is not None and len(lucro.findall(q("item"))) == 3
    assert jcp is not None and len(jcp.findall(q("item"))) == 2


def test_dry_run_nao_altera_xml(tmp_path: Path) -> None:
    xml = tmp_path / "decl.xml"
    csv = tmp_path / "prov.csv"
    write_minimal_xml(xml)
    write_csv_ok(csv)
    before = xml.read_text(encoding="utf-8")

    stats = import_proventos(xml, csv, mode="dry-run")

    assert stats.dry_run is True
    assert xml.read_text(encoding="utf-8") == before
