from datetime import datetime
from decimal import Decimal

import pytest

from lucky_receipt.services import QRParseError, parse_qr_string


def test_parse_valid():
    result = parse_qr_string("t=20250101T1200&s=1500.00&fn=1234567890123456&i=12345&fp=9876543210&n=1")
    assert result.fn == "1234567890123456"
    assert result.fd == "12345"
    assert result.fp == "9876543210"
    assert result.amount == Decimal("1500.00")
    assert result.purchased_at == datetime(2025, 1, 1, 12, 0)


def test_parse_alt_date_format():
    result = parse_qr_string("t=2025-01-01T12:00&s=1000&fn=1&i=2&fp=3")
    assert result.purchased_at == datetime(2025, 1, 1, 12, 0)


def test_missing_field():
    with pytest.raises(QRParseError, match="fn"):
        parse_qr_string("t=20250101T1200&s=1500&i=1&fp=3")


def test_non_digits():
    with pytest.raises(QRParseError, match="только из цифр"):
        parse_qr_string("t=20250101T1200&s=1500&fn=abc&i=1&fp=3")


def test_bad_date():
    with pytest.raises(QRParseError, match="дату"):
        parse_qr_string("t=not-a-date&s=1500&fn=1&i=2&fp=3")


def test_zero_amount():
    with pytest.raises(QRParseError, match="больше нуля"):
        parse_qr_string("t=20250101T1200&s=0&fn=1&i=2&fp=3")


def test_empty():
    with pytest.raises(QRParseError):
        parse_qr_string("")
