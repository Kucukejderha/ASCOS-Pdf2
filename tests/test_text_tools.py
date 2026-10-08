from __future__ import annotations

from pathlib import Path

import pymupdf

from app.core.pdf_editor.text_tools import extract_rect_text, span_at_point, words_in_rect


def test_extract_single_line(digital_pdf: Path) -> None:
    with pymupdf.open(str(digital_pdf)) as doc:
        page = doc[0]
        text = extract_rect_text(page, (50, 55, 400, 80))
        assert text == "MERHABA DUNYA"


def test_extract_multiple_lines(digital_pdf: Path) -> None:
    with pymupdf.open(str(digital_pdf)) as doc:
        page = doc[0]
        text = extract_rect_text(page, (50, 55, 430, 100))
        lines = text.splitlines()
        assert lines[0] == "MERHABA DUNYA"
        assert lines[1] == "Bu bir test belgesidir."


def test_empty_area_returns_empty(digital_pdf: Path) -> None:
    with pymupdf.open(str(digital_pdf)) as doc:
        page = doc[0]
        assert extract_rect_text(page, (460, 400, 560, 500)) == ""


def test_words_in_rect(digital_pdf: Path) -> None:
    with pymupdf.open(str(digital_pdf)) as doc:
        page = doc[0]
        words = words_in_rect(page, pymupdf.Rect(50, 55, 400, 80))
        joined = " ".join(w[4] for w in words)
        assert joined == "MERHABA DUNYA"


def test_span_at_point(digital_pdf: Path) -> None:
    with pymupdf.open(str(digital_pdf)) as doc:
        page = doc[0]
        span = None
        data = page.get_text("dict")
        for block in data["blocks"]:
            if block.get("type") != 0:
                continue
            for line in block["lines"]:
                for candidate in line["spans"]:
                    if "MERHABA" in candidate["text"]:
                        span = candidate
                        break
        assert span is not None
        x0, y0, x1, y1 = span["bbox"]
        found = span_at_point(page, pymupdf.Point((x0 + x1) / 2, (y0 + y1) / 2))
        assert found is not None
        assert "MERHABA" in found["text"]
        assert found["size"] > 0
