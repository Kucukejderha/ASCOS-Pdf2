from __future__ import annotations

import pytest

from app.core.utils import parse_number, parse_page_range


def test_parse_page_range_basic() -> None:
    assert parse_page_range("1-3,5", 10) == [0, 1, 2, 4]
    assert parse_page_range("2", 5) == [1]
    assert parse_page_range("", 5) is None
    assert parse_page_range("3-1", 5) == [0, 1, 2]


def test_parse_page_range_clamps_and_sorts() -> None:
    assert parse_page_range("9-12", 10) == [8, 9]
    assert parse_page_range("5,2,3", 10) == [1, 2, 4]


def test_parse_page_range_invalid() -> None:
    with pytest.raises(ValueError):
        parse_page_range("abc", 10)
    with pytest.raises(ValueError):
        parse_page_range("99", 10)


def test_parse_number_turkish() -> None:
    assert parse_number("1.234,56") == pytest.approx(1234.56)
    assert parse_number("42,75") == pytest.approx(42.75)
    assert parse_number("3") == 3
    assert isinstance(parse_number("3"), int)
    assert parse_number("Kalem") == "Kalem"
    assert parse_number("") == ""


def test_parse_number_english() -> None:
    assert parse_number("1,234.56") == pytest.approx(1234.56)
    assert parse_number("15.50") == pytest.approx(15.5)
    assert parse_number("1.234.567") == 1234567
