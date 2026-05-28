from __future__ import annotations

from decimal import Decimal, InvalidOperation


def br_money_to_decimal(value: str | None) -> Decimal:
    value = (value or "0,00").strip()
    if not value:
        return Decimal("0.00")
    normalized = value.replace(".", "").replace(",", ".")
    try:
        return Decimal(normalized)
    except InvalidOperation as exc:
        raise ValueError(f"Valor monetário inválido: {value!r}") from exc


def decimal_to_br_money(value: Decimal) -> str:
    value = value.quantize(Decimal("0.01"))
    s = f"{value:.2f}"
    inteiro, dec = s.split(".")
    negative = inteiro.startswith("-")
    if negative:
        inteiro = inteiro[1:]
    partes: list[str] = []
    while len(inteiro) > 3:
        partes.insert(0, inteiro[-3:])
        inteiro = inteiro[:-3]
    partes.insert(0, inteiro or "0")
    return ("-" if negative else "") + ".".join(partes) + "," + dec
