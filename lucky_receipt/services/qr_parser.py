from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from urllib.parse import parse_qs


class QRParseError(ValueError):
    """Ошибка разбора строки из QR-кода."""


@dataclass(frozen=True, slots=True)
class ParsedQR:
    fn: str
    fd: str
    fp: str
    purchased_at: datetime
    amount: Decimal


QR_DATE_FORMATS = (
    "%Y%m%dT%H%M%S",
    "%Y%m%dT%H%M",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M",
)

MAX_LEN = {"fn": 16, "i": 20, "fp": 20}


def parse_qr_string(raw: str) -> ParsedQR:
    if not raw or not isinstance(raw, str):
        raise QRParseError("Пустая строка QR-кода")

    raw = raw.strip()

    try:
        data = parse_qs(raw, strict_parsing=False, keep_blank_values=False)
    except ValueError as exc:
        raise QRParseError("Не удалось разобрать строку QR-кода") from exc

    def one(key: str) -> str:
        values = data.get(key)
        if not values or not values[0]:
            raise QRParseError(f"В строке отсутствует параметр '{key}'")
        return values[0].strip()

    fn = one("fn")
    fd = one("i")       # в QR это 'i', у нас в модели — fd
    fp = one("fp")
    t_raw = one("t")
    s_raw = one("s")

    for key, value in (("fn", fn), ("i", fd), ("fp", fp)):
        if not value.isdigit():
            raise QRParseError(f"Параметр '{key}' должен состоять только из цифр")
        if len(value) > MAX_LEN[key]:
            raise QRParseError(f"Параметр '{key}' слишком длинный")

    purchased_at = None
    for fmt in QR_DATE_FORMATS:
        try:
            purchased_at = datetime.strptime(t_raw, fmt)
            break
        except ValueError:
            continue
    if purchased_at is None:
        raise QRParseError(f"Не удалось разобрать дату покупки: '{t_raw}'")

    try:
        amount = Decimal(s_raw.replace(",", "."))
    except InvalidOperation as exc:
        raise QRParseError(f"Некорректная сумма: '{s_raw}'") from exc

    if amount <= 0:
        raise QRParseError("Сумма должна быть больше нуля")

    return ParsedQR(fn=fn, fd=fd, fp=fp, purchased_at=purchased_at, amount=amount)
