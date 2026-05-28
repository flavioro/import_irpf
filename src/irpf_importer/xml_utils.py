from __future__ import annotations

import xml.etree.ElementTree as ET

NS = "http://www.receita.fazenda.gov.br/declaracao"
ET.register_namespace("", NS)


def q(tag: str) -> str:
    return f"{{{NS}}}{tag}"


def find_required(root: ET.Element, tag: str) -> ET.Element:
    el = root.find(q(tag))
    if el is None:
        raise RuntimeError(f"Tag obrigatória não encontrada no XML: {tag}")
    return el


def find_resumo_outras_info(root: ET.Element) -> ET.Element | None:
    resumo = root.find(q("resumo"))
    if resumo is None:
        return None
    return resumo.find(q("outrasInformacoes"))


def clear_children(el: ET.Element) -> None:
    for child in list(el):
        el.remove(child)
