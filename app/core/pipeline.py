from __future__ import annotations

from pathlib import Path
from typing import Callable

from app.core.converter import (
    convert_pdf_to_excel,
    convert_pdf_to_word,
    get_engine,
    OcrError,
    RapidOcrEngine,
    TesseractEngine,
)
from app.core.models import ConversionOptions, ConversionResult, ConvertMode

ProgressCb = Callable[[float, str], None]

SUFFIX = {ConvertMode.WORD: ".docx", ConvertMode.EXCEL: ".xlsx"}


def default_output_path(src: Path, mode: ConvertMode, output_dir: Path | None = None) -> Path:
    folder = output_dir if output_dir else src.parent
    return folder / (src.stem + SUFFIX[mode])


def convert(
    src: str | Path,
    options: ConversionOptions,
    output_dir: Path | None = None,
    progress: ProgressCb | None = None,
) -> ConversionResult:
    src = Path(src)
    if src.suffix.lower() != ".pdf":
        raise ValueError(f"Desteklenmeyen dosya türü: {src.suffix}")
    dst = default_output_path(src, options.mode, output_dir)
    if options.mode == ConvertMode.WORD:
        return convert_pdf_to_word(src, dst, options, progress)
    return convert_pdf_to_excel(src, dst, options, progress)


def available_ocr_engines() -> list[str]:
    engines: list[str] = []
    tesseract = TesseractEngine()
    if tesseract.available():
        langs = tesseract.languages
        engines.append("tesseract" + (f" ({', '.join(langs[:6])})" if langs else ""))
    rapid = RapidOcrEngine()
    if rapid.available():
        engines.append("rapidocr")
    return engines


def preferred_engine() -> str:
    for engine in (TesseractEngine(), RapidOcrEngine()):
        if engine.available():
            return engine.name
    raise OcrError("Kullanılabilir OCR motoru yok")
