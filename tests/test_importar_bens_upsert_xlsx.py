from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET

from openpyxl import Workbook

from irpf_importer.importers.bens import import_bens, q
from tests.test_importar_bens import write_sample_xml


def write_xlsx(path: Path) -> None:
    wb = Workbook()
    ws = wb.active
    ws.append(["acao", "grupo", "codigo", "discriminacao", "valorExercicioAnterior", "valorExercicioAtual", "registroBem"])
    ws.append(["upsert", "02", "01", "BEM ORIGINAL 1", "9.000,00", "11.000,00", "ABC"])
    ws.append(["upsert", "07", "03", "FII NOVO", "0,00", "1.500,00", "FII-001"])
    wb.save(path)


def test_import_bens_upsert_from_xlsx_updates_and_inserts(tmp_path: Path):
    xml = tmp_path / "dec.xml"
    xlsx = tmp_path / "bens.xlsx"
    write_sample_xml(xml)
    write_xlsx(xlsx)

    stats = import_bens(xml, xlsx, mode="upsert")

    assert stats.updated == 1
    assert stats.added == 1
    assert stats.removed == 0
    assert stats.total_items == 3
    assert stats.total_exercicio_atual == "12.500,00"

    bens = ET.parse(xml).getroot().find(q("bens"))
    assert bens is not None
    items = bens.findall(q("item"))
    assert len(items) == 3
    updated = next(item for item in items if item.attrib.get("registroBem") == "ABC")
    inserted = next(item for item in items if item.attrib.get("registroBem") == "FII-001")
    assert updated.attrib["valorExercicioAtual"] == "11.000,00"
    assert inserted.attrib["discriminacao"] == "FII NOVO"
