from __future__ import annotations

import argparse
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from .conf import recalcular_conf

NS = "http://www.receita.fazenda.gov.br/declaracao"
ET.register_namespace("", NS)

SUPPORTED_CLONE_MODES = ("identidade", "template-limpo", "anonimo")
ZERO_MONEY = "0,00"

IDENTIFIER_TAGS = ("identificadorDec", "identificadorDeclaracao", "copiaIdentificador")
RECEIPT_ATTRS = ("numeroReciboDecAnterior", "numReciboDecRetif", "numReciboTransmitido")
BLANK_CPF = "   .   .   -  "


def q(tag: str) -> str:
    return f"{{{NS}}}{tag}"


def only_digits(value: str | None) -> str:
    return re.sub(r"\D+", "", value or "")


def format_cpf(cpf: str) -> str:
    digits = only_digits(cpf)
    if len(digits) != 11:
        raise ValueError(f"CPF deve ter 11 dígitos. Recebido: {cpf!r}")
    return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"


def unformat_cpf(cpf: str) -> str:
    digits = only_digits(cpf)
    if len(digits) != 11:
        raise ValueError(f"CPF deve ter 11 dígitos. Recebido: {cpf!r}")
    return digits


def find_first(root: ET.Element, path: str) -> ET.Element | None:
    return root.find(path)


def find_required(root: ET.Element, tag: str) -> ET.Element:
    el = root.find(q(tag))
    if el is None:
        raise RuntimeError(f"Tag obrigatória não encontrada no XML: {tag}")
    return el


def remove_item_children(parent: ET.Element | None) -> int:
    if parent is None:
        return 0
    removed = 0
    for child in list(parent):
        if child.tag == q("item"):
            parent.remove(child)
            removed += 1
    return removed


def remove_all_children(parent: ET.Element | None) -> int:
    if parent is None:
        return 0
    removed = len(list(parent))
    for child in list(parent):
        parent.remove(child)
    return removed


def is_money_like(value: str) -> bool:
    return bool(re.fullmatch(r"-?\d{1,3}(?:\.\d{3})*,\d{2,4}|-?\d+,\d{2,4}", value or ""))


def zero_money_attrs(element: ET.Element | None) -> None:
    if element is None:
        return
    for key, value in list(element.attrib.items()):
        if is_money_like(value):
            # Alguns campos usam quatro casas, como totalDeducaoIncentivo="0,0000".
            element.attrib[key] = "0,0000" if value.endswith(",0000") else ZERO_MONEY


def zero_money_attrs_recursive(element: ET.Element | None) -> None:
    if element is None:
        return
    zero_money_attrs(element)
    for child in list(element):
        zero_money_attrs_recursive(child)


@dataclass(frozen=True)
class CloneStats:
    mode: str
    dry_run: bool
    source_xml: Path
    target_xml: Path
    target_conf: Path
    target_cpf: str
    target_name: str
    removed_items: int
    cleaned_financial_sections: bool


@dataclass(frozen=True)
class CloneResult:
    stats: CloneStats
    backup_dir: Path | None = None


def update_common_identity(
    root: ET.Element,
    *,
    target_cpf: str,
    target_name: str,
    email: str = "",
    telefone: str = "",
    ddd: str = "",
    celular: str = "",
    ddd_celular: str = "",
    titulo_eleitor: str = "0000000000000",
    data_nascimento: str = "",
    cep: str = "",
    tipo_logradouro: str = "RUA",
    logradouro: str = "",
    numero: str = "",
    complemento: str = "",
    bairro: str = "",
    municipio: str = "0000",
    uf: str = "",
    natureza_ocupacao: str = "01",
    ocupacao_principal: str = "519",
    cpf_conjuge: str = "",
) -> None:
    cpf_fmt = format_cpf(target_cpf)
    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    root.attrib["dataHoraSalvamento"] = now
    root.attrib["utlimoCPFAutenticado"] = BLANK_CPF

    contribuinte = root.find(q("contribuinte"))
    if contribuinte is not None:
        updates = {
            "email": email,
            "telefone": telefone,
            "ddd": ddd,
            "celular": celular,
            "dddCelular": ddd_celular,
            "tituloEleitor": titulo_eleitor,
            "dataNascimento": data_nascimento,
            "cep": cep,
            "tipoLogradouro": tipo_logradouro,
            "logradouro": logradouro,
            "numero": numero,
            "complemento": complemento,
            "bairro": bairro,
            "municipio": municipio,
            "uf": uf,
            "naturezaOcupacao": natureza_ocupacao,
            "ocupacaoPrincipal": ocupacao_principal,
            "cpfConjuge": format_cpf(cpf_conjuge) if only_digits(cpf_conjuge) else BLANK_CPF,
            "cpfProcurador": BLANK_CPF,
        }
        for key, value in updates.items():
            if key in contribuinte.attrib or value:
                contribuinte.attrib[key] = value

    for ident_tag in IDENTIFIER_TAGS:
        for ident in root.findall(f".//{q(ident_tag)}"):
            ident.attrib["cpf"] = cpf_fmt
            ident.attrib["nome"] = target_name
            for receipt_attr in RECEIPT_ATTRS:
                ident.attrib[receipt_attr] = ""
            ident.attrib["transmitida"] = "0"
            ident.attrib["tpTransmitida"] = ""
            ident.attrib["declaracaoRetificadora"] = "0"
            ident.attrib["dataUltimoAcesso"] = now

    # CPFs do próprio titular aparecem em subitens, como cpfBeneficiario.
    for element in root.iter():
        if "cpfBeneficiario" in element.attrib:
            element.attrib["cpfBeneficiario"] = cpf_fmt
        # Estes campos não devem vir do contribuinte antigo por padrão.
        for cpf_attr in ("cpfAlimentante", "cpfProcurador", "cpfInventariante"):
            if cpf_attr in element.attrib:
                element.attrib[cpf_attr] = BLANK_CPF


def anonymize_extra_personal_data(root: ET.Element, target_name: str) -> None:
    # Remove pessoas relacionadas; mantém apenas a estrutura das coleções.
    for tag in ("dependentes", "alimentandos", "herdeiros"):
        remove_all_children(root.find(q(tag)))

    espolio = root.find(q("espolio"))
    if espolio is not None:
        for attr in ("anoObito", "nomeInventariante", "nomeConjugeCompanheiro"):
            if attr in espolio.attrib:
                espolio.attrib[attr] = ""
        for element in espolio.iter():
            for attr in ("cpfInventariante", "nomeInventariante", "nomeConjugeCompanheiro"):
                if attr in element.attrib:
                    element.attrib[attr] = BLANK_CPF if attr.startswith("cpf") else ""


def clean_financial_sections(root: ET.Element) -> int:
    removed = 0

    # Rendimentos PJ e exigibilidade.
    for path in [
        f".//{q('colecaoRendPJTitular')}",
        f".//{q('colecaoRendPJDependente')}",
        f".//{q('colecaoRendPJComExigibilidadeTitular')}",
        f".//{q('colecaoRendPJComExigibilidadeDependente')}",
        f".//{q('colecaoRendAcmTitular')}",
        f".//{q('colecaoRendAcmDependente')}",
    ]:
        for parent in root.findall(path):
            removed += remove_item_children(parent)
            zero_money_attrs(parent)

    # Rendimentos isentos e tributação exclusiva: quadros auxiliares possuem itens.
    for container_tag in ("rendIsentos", "rendTributacaoExclusiva"):
        container = root.find(q(container_tag))
        if container is not None:
            for child in list(container):
                removed += remove_item_children(child)
                if "totais" in child.attrib:
                    child.attrib["totais"] = ZERO_MONEY
                zero_money_attrs(child)
            zero_money_attrs(container)
            if "total" in container.attrib:
                container.attrib["total"] = ZERO_MONEY

    # Coleções diretas comuns.
    for tag in ("pagamentos", "doacoes", "bens", "dividas", "doacoesEleitorais"):
        el = root.find(q(tag))
        if el is not None:
            removed += remove_item_children(el)
            zero_money_attrs(el)
            if tag == "bens":
                el.attrib["totalItens"] = "0"
                el.attrib["ultimoIndiceGerado"] = ""
                el.attrib["totalExercicioAnterior"] = ZERO_MONEY
                el.attrib["totalExercicioAtual"] = ZERO_MONEY
            if "ultimoIndiceGerado" in el.attrib:
                el.attrib["ultimoIndiceGerado"] = ""

    # Atividade rural, renda variável e fundos: mantém meses/estrutura, zera valores e remove coleções.
    for tag in ("rendPFTitular", "rendPFDependente", "rendaVariavel", "rendaVariavelDependente", "fundosInvestimentos", "fundosInvestimentosDependente", "atividadeRural"):
        zero_money_attrs_recursive(root.find(q(tag)))

    atividade = root.find(q("atividadeRural"))
    if atividade is not None:
        for element in atividade.iter():
            removed += remove_item_children(element)
            if "ultimoIndiceGerado" in element.attrib:
                element.attrib["ultimoIndiceGerado"] = ""

    # Resumo/calculo: zera totais financeiros, preservando identificadores que serão atualizados por identity.
    resumo = root.find(q("resumo"))
    if resumo is not None:
        for child in list(resumo):
            if child.tag not in (q("identificadorDeclaracao"),):
                zero_money_attrs_recursive(child)

    # Comparativo.
    zero_money_attrs_recursive(root.find(q("comparativo")))

    return removed


def clone_declaration(
    *,
    source_xml: Path,
    target_dir: Path,
    target_cpf: str,
    target_name: str,
    mode: str,
    irpf_dir: Path | None = None,
    backup_dir: Path | None = None,
    dry_run: bool = False,
    recalc_conf: bool = True,
    email: str = "",
    telefone: str = "",
    ddd: str = "",
    celular: str = "",
    ddd_celular: str = "",
    titulo_eleitor: str = "0000000000000",
    data_nascimento: str = "",
    cep: str = "",
    tipo_logradouro: str = "RUA",
    logradouro: str = "",
    numero: str = "",
    complemento: str = "",
    bairro: str = "",
    municipio: str = "0000",
    uf: str = "",
    natureza_ocupacao: str = "01",
    ocupacao_principal: str = "519",
    cpf_conjuge: str = "",
) -> CloneResult:
    mode = mode.strip().lower()
    if mode not in SUPPORTED_CLONE_MODES:
        raise ValueError(f"Modo inválido: {mode}. Use: {', '.join(SUPPORTED_CLONE_MODES)}")

    source_xml = Path(source_xml)
    target_dir = Path(target_dir)
    target_cpf_digits = unformat_cpf(target_cpf)
    target_folder = target_dir / target_cpf_digits
    target_xml = target_folder / f"{target_cpf_digits}-0000000000.xml"
    target_conf = target_folder / f"{target_cpf_digits}-0000000000.conf"

    tree = ET.parse(source_xml)
    root = tree.getroot()

    update_common_identity(
        root,
        target_cpf=target_cpf_digits,
        target_name=target_name,
        email=email,
        telefone=telefone,
        ddd=ddd,
        celular=celular,
        ddd_celular=ddd_celular,
        titulo_eleitor=titulo_eleitor,
        data_nascimento=data_nascimento,
        cep=cep,
        tipo_logradouro=tipo_logradouro,
        logradouro=logradouro,
        numero=numero,
        complemento=complemento,
        bairro=bairro,
        municipio=municipio,
        uf=uf,
        natureza_ocupacao=natureza_ocupacao,
        ocupacao_principal=ocupacao_principal,
        cpf_conjuge=cpf_conjuge,
    )

    removed = 0
    cleaned = False
    if mode in ("template-limpo", "anonimo"):
        anonymize_extra_personal_data(root, target_name)
        removed += clean_financial_sections(root)
        cleaned = True
    elif mode == "identidade":
        # Mantém dados financeiros, mas remove relações pessoais que podem vazar dados de terceiro.
        anonymize_extra_personal_data(root, target_name)

    stats = CloneStats(
        mode=mode,
        dry_run=dry_run,
        source_xml=source_xml,
        target_xml=target_xml,
        target_conf=target_conf,
        target_cpf=target_cpf_digits,
        target_name=target_name,
        removed_items=removed,
        cleaned_financial_sections=cleaned,
    )

    if dry_run:
        return CloneResult(stats=stats)

    target_folder.mkdir(parents=True, exist_ok=True)

    if backup_dir is not None:
        backup_dir = Path(backup_dir)
        backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if target_folder.exists():
            backup_target = backup_dir / f"backup_clone_{target_cpf_digits}_{stamp}"
            if any(target_folder.iterdir()):
                shutil.copytree(target_folder, backup_target, dirs_exist_ok=True)

    tree.write(target_xml, encoding="utf-8", xml_declaration=True)

    if recalc_conf:
        if irpf_dir is None:
            raise RuntimeError("--irpf-dir é obrigatório para recalcular o .conf.")
        recalcular_conf(Path(irpf_dir), target_xml)
    else:
        # Não cria .conf vazio: deixa um marcador explícito para evitar confusão com hash válido.
        target_conf.with_suffix(".conf.pending").write_text("CONF pendente: execute recálculo no IRPF antes de usar a declaração.\n", encoding="utf-8")

    return CloneResult(stats=stats, backup_dir=backup_dir)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Clona/sanitiza XML do IRPF 2026 para outro CPF.")
    parser.add_argument("--mode", required=True, choices=SUPPORTED_CLONE_MODES)
    parser.add_argument("--source-xml", required=True)
    parser.add_argument("--target-dir", required=True, help="Normalmente: C:\\Arquivos de Programas RFB\\IRPF2026\\aplicacao\\dados")
    parser.add_argument("--target-cpf", required=True)
    parser.add_argument("--target-name", required=True)
    parser.add_argument("--irpf-dir", required=False, help="Obrigatório se recalcular .conf")
    parser.add_argument("--backup-dir", required=False)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--sem-recalcular-conf", action="store_true")

    parser.add_argument("--email", default="")
    parser.add_argument("--telefone", default="")
    parser.add_argument("--ddd", default="")
    parser.add_argument("--celular", default="")
    parser.add_argument("--ddd-celular", default="")
    parser.add_argument("--titulo-eleitor", default="0000000000000")
    parser.add_argument("--data-nascimento", default="")
    parser.add_argument("--cep", default="")
    parser.add_argument("--tipo-logradouro", default="RUA")
    parser.add_argument("--logradouro", default="")
    parser.add_argument("--numero", default="")
    parser.add_argument("--complemento", default="")
    parser.add_argument("--bairro", default="")
    parser.add_argument("--municipio", default="0000")
    parser.add_argument("--uf", default="")
    parser.add_argument("--natureza-ocupacao", default="01")
    parser.add_argument("--ocupacao-principal", default="519")
    parser.add_argument("--cpf-conjuge", default="")
    return parser


def print_result(result: CloneResult) -> None:
    s = result.stats
    if s.dry_run:
        print("DRY-RUN: nenhum arquivo foi alterado e o .conf não foi recalculado.")
    print(f"Modo: {s.mode}")
    print(f"CPF destino: {s.target_cpf}")
    print(f"Nome destino: {s.target_name}")
    print(f"XML origem: {s.source_xml}")
    print(f"XML destino: {s.target_xml}")
    print(f"CONF destino: {s.target_conf}")
    print(f"Itens removidos/limpos: {s.removed_items}")
    print(f"Fichas financeiras limpas: {'sim' if s.cleaned_financial_sections else 'não'}")
    if result.backup_dir:
        print(f"Backup dir: {result.backup_dir}")
    print("Abra o IRPF e valide a declaração pela interface oficial antes de usar qualquer dado real.")


def main() -> None:
    args = build_arg_parser().parse_args()
    result = clone_declaration(
        source_xml=Path(args.source_xml),
        target_dir=Path(args.target_dir),
        target_cpf=args.target_cpf,
        target_name=args.target_name,
        mode=args.mode,
        irpf_dir=Path(args.irpf_dir) if args.irpf_dir else None,
        backup_dir=Path(args.backup_dir) if args.backup_dir else None,
        dry_run=args.dry_run,
        recalc_conf=not args.sem_recalcular_conf,
        email=args.email,
        telefone=args.telefone,
        ddd=args.ddd,
        celular=args.celular,
        ddd_celular=args.ddd_celular,
        titulo_eleitor=args.titulo_eleitor,
        data_nascimento=args.data_nascimento,
        cep=args.cep,
        tipo_logradouro=args.tipo_logradouro,
        logradouro=args.logradouro,
        numero=args.numero,
        complemento=args.complemento,
        bairro=args.bairro,
        municipio=args.municipio,
        uf=args.uf,
        natureza_ocupacao=args.natureza_ocupacao,
        ocupacao_principal=args.ocupacao_principal,
        cpf_conjuge=args.cpf_conjuge,
    )
    print_result(result)


if __name__ == "__main__":
    main()
