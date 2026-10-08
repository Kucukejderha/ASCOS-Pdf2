from __future__ import annotations

import io
import shutil
from typing import TYPE_CHECKING

import pymupdf

if TYPE_CHECKING:
    from PIL.Image import Image as PILImage

DEFAULT_DPI = 300


class OcrError(RuntimeError):
    pass


class OcrEngine:
    name = "temel"

    def available(self) -> bool:
        raise NotImplementedError

    def recognize(self, image: "PILImage", lang: str) -> str:
        raise NotImplementedError


class TesseractEngine(OcrEngine):
    name = "Tesseract"

    def __init__(self) -> None:
        self._checked: bool | None = None
        self._langs: list[str] = []

    def available(self) -> bool:
        if self._checked is None:
            self._checked = shutil.which("tesseract") is not None
            if self._checked:
                try:
                    import pytesseract

                    self._langs = pytesseract.get_languages(config="")
                except Exception:
                    self._checked = False
        return bool(self._checked)

    @property
    def languages(self) -> list[str]:
        self.available()
        return list(self._langs)

    def resolve_lang(self, lang: str) -> str:
        if not self._langs:
            return lang
        requested = [p for p in lang.split("+") if p]
        found = [p for p in requested if p in self._langs]
        if not found:
            return "eng" if "eng" in self._langs else self._langs[0]
        return "+".join(found)

    def recognize(self, image: "PILImage", lang: str) -> str:
        import pytesseract

        return pytesseract.image_to_string(image, lang=self.resolve_lang(lang))


class RapidOcrEngine(OcrEngine):
    name = "RapidOCR"

    def __init__(self) -> None:
        self._engine = None
        self._checked: bool | None = None

    def available(self) -> bool:
        if self._checked is None:
            try:
                import rapidocr_onnxruntime  # noqa: F401

                self._checked = True
            except Exception:
                self._checked = False
        return bool(self._checked)

    def recognize(self, image: "PILImage", lang: str) -> str:
        import numpy as np
        from rapidocr_onnxruntime import RapidOCR

        if self._engine is None:
            self._engine = RapidOCR()
        result, _ = self._engine(np.array(image))
        if not result:
            return ""
        return "\n".join(line[1] for line in result)


def get_engine(preference: str = "auto") -> OcrEngine:
    """OCR motoru seçer. preference: auto | tesseract | rapidocr."""
    tesseract = TesseractEngine()
    if preference == "tesseract":
        if tesseract.available():
            return tesseract
        raise OcrError("Tesseract kurulu değil veya bulunamadı")
    if preference == "rapidocr":
        rapid = RapidOcrEngine()
        if rapid.available():
            return rapid
        raise OcrError("RapidOCR kurulu değil")
    if tesseract.available():
        return tesseract
    rapid = RapidOcrEngine()
    if rapid.available():
        return rapid
    raise OcrError("Kullanılabilir OCR motoru yok")


def render_page(page: pymupdf.Page, dpi: int = DEFAULT_DPI) -> "PILImage":
    from PIL import Image

    pix = page.get_pixmap(dpi=dpi)
    data = pix.tobytes("png")
    return Image.open(io.BytesIO(data)).convert("RGB")


def ocr_page(page: pymupdf.Page, engine: OcrEngine, lang: str = "tur+eng", dpi: int = DEFAULT_DPI) -> str:
    image = render_page(page, dpi=dpi)
    return engine.recognize(image, lang)
