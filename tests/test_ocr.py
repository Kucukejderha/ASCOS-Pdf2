from __future__ import annotations

from pathlib import Path

from docx import Document
from PIL import Image
import pytest

from app.core.converter.ocr import OcrError, RapidOcrEngine, TesseractEngine, get_engine
from app.core.models import ConversionOptions, ConvertMode
from app.core.pipeline import convert


def test_get_engine_returns_available_engine() -> None:
    engine = get_engine("auto")
    assert engine.available()
    assert engine.name in {"Tesseract", "RapidOCR"}


def test_get_engine_missing_preference() -> None:
    if TesseractEngine().available():
        pytest.skip("Tesseract kurulu, bu senaryo atlandı")
    with pytest.raises(OcrError):
        get_engine("tesseract")


def test_rapidocr_recognizes_text(ocr_image: Image.Image) -> None:
    engine = RapidOcrEngine()
    if not engine.available():
        pytest.skip("RapidOCR kurulu değil")
    text = engine.recognize(ocr_image, "tur+eng")
    normalized = text.upper()
    assert "TEST" in normalized or "123" in normalized


@pytest.mark.slow
def test_scanned_pdf_to_word_with_ocr(scanned_pdf: Path, tmp_path: Path) -> None:
    result = convert(
        scanned_pdf,
        ConversionOptions(mode=ConvertMode.WORD, ocr=True, ocr_engine="rapidocr"),
        output_dir=tmp_path,
    )
    assert result.output.exists()
    assert result.ocr_pages == [0]
    text = "\n".join(p.text for p in Document(str(result.output)).paragraphs).upper()
    compact = "".join(ch for ch in text if ch.isalpha())
    assert "TARANMIS" in compact or "TARANMI" in compact
