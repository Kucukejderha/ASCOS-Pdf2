from __future__ import annotations

from pathlib import Path

from app.core.converter import analyze_pdf


def test_digital_pdf_not_scanned(digital_pdf: Path) -> None:
    analysis = analyze_pdf(digital_pdf)
    assert analysis.page_count == 2
    assert analysis.is_fully_digital
    assert not analysis.is_fully_scanned
    assert analysis.scanned_pages == []


def test_scanned_pdf_detected(scanned_pdf: Path) -> None:
    analysis = analyze_pdf(scanned_pdf)
    assert analysis.page_count == 1
    assert analysis.is_fully_scanned
    assert analysis.scanned_pages == [0]


def test_mixed_pdf_detected(mixed_pdf: Path) -> None:
    analysis = analyze_pdf(mixed_pdf)
    assert analysis.page_count == 2
    assert not analysis.is_fully_scanned
    assert not analysis.is_fully_digital
    assert analysis.scanned_pages == [1]
