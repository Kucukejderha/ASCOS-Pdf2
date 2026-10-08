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

    def recognize_lines(
        self, image: "PILImage", lang: str
    ) -> list[tuple[list[tuple[float, float]], str, float]]:
        """Metin satırlarını kutu koordinatlarıyla döndürür.

        Her öğe: (kutu_noktaları, metin, güven). Kutu noktaları görüntü piksel
        koordinatındadır.
        """
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

    def recognize_lines(
        self, image: "PILImage", lang: str
    ) -> list[tuple[list[tuple[float, float]], str, float]]:
        import pytesseract
        from pytesseract import Output

        data = pytesseract.image_to_data(
            image, lang=self.resolve_lang(lang), output_type=Output.DICT
        )
        lines: dict[tuple, dict] = {}
        for i in range(len(data["text"])):
            word = str(data["text"][i]).strip()
            if not word:
                continue
            try:
                confidence = float(data["conf"][i])
            except (TypeError, ValueError):
                confidence = 0.0
            key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
            entry = lines.setdefault(
                key,
                {"x0": 1e9, "y0": 1e9, "x1": -1e9, "y1": -1e9, "words": [], "conf": []},
            )
            x, y = data["left"][i], data["top"][i]
            w, h = data["width"][i], data["height"][i]
            entry["x0"] = min(entry["x0"], x)
            entry["y0"] = min(entry["y0"], y)
            entry["x1"] = max(entry["x1"], x + w)
            entry["y1"] = max(entry["y1"], y + h)
            entry["words"].append(word)
            entry["conf"].append(confidence)

        result = []
        for entry in lines.values():
            box = [
                (entry["x0"], entry["y0"]),
                (entry["x1"], entry["y0"]),
                (entry["x1"], entry["y1"]),
                (entry["x0"], entry["y1"]),
            ]
            confidence = (
                sum(entry["conf"]) / len(entry["conf"]) / 100 if entry["conf"] else 0.0
            )
            result.append((box, " ".join(entry["words"]), confidence))
        return result


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

    def recognize_lines(
        self, image: "PILImage", lang: str
    ) -> list[tuple[list[tuple[float, float]], str, float]]:
        import numpy as np
        from rapidocr_onnxruntime import RapidOCR

        if self._engine is None:
            self._engine = RapidOCR()
        result, _ = self._engine(np.array(image))
        if not result:
            return []
        lines = []
        for box, text, score in result:
            points = [(float(p[0]), float(p[1])) for p in box]
            lines.append((points, str(text), float(score)))
        return lines


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
