from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable


def _cell_to_str(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def read_table_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    """Lê CSV ou XLSX e retorna cabeçalhos e linhas como strings.

    O XLSX usa a primeira aba e a primeira linha como cabeçalho.
    """
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None:
                raise RuntimeError("Arquivo sem cabeçalho.")
            rows = [{k: _cell_to_str(v) for k, v in row.items() if k is not None} for row in reader]
            return list(reader.fieldnames), rows

    if suffix in {".xlsx", ".xlsm"}:
        try:
            from openpyxl import load_workbook
        except ImportError as exc:
            raise RuntimeError("Para ler XLSX instale a dependência openpyxl.") from exc
        wb = load_workbook(path, read_only=True, data_only=True)
        ws = wb.active
        values = list(ws.iter_rows(values_only=True))
        if not values:
            raise RuntimeError("Planilha sem cabeçalho.")
        fieldnames = [_cell_to_str(v) for v in values[0]]
        if not any(fieldnames):
            raise RuntimeError("Planilha sem cabeçalho.")
        rows: list[dict[str, str]] = []
        for row_values in values[1:]:
            row = {fieldnames[i]: _cell_to_str(row_values[i] if i < len(row_values) else "") for i in range(len(fieldnames)) if fieldnames[i]}
            if any(row.values()):
                rows.append(row)
        return fieldnames, rows

    raise RuntimeError(f"Formato não suportado: {path.suffix}. Use .csv, .xlsx ou .xlsm.")
