"""Taranmış sayfaları pdf2docx'in işleyebileceği yeniden inşa PDF'ine dönüştürür.

pdf2docx düzen/tablo çıkarımı için metin katmanı ve vektör çizgilere ihtiyaç
duyar; taramalarda ikisi de yoktur. Ayrıca pdf2docx görünmez (render_mode=3)
metni bilinçli olarak süzer. Bu modül her taranmış sayfayı:

1. 300 DPI render eder,
2. OpenCV ile yatay/dikey tablo kenarlıklarını tespit eder,
3. boş sayfa üzerine kenarlıkları vektör çizgi, OCR satırlarını konumlarına
   yerleştirilmiş görünür metin olarak yazar (tarama görüntüsü eklenmez;
   amaç düzenlenebilir tablo/metin çıktısıdır).

Dijital sayfalar aynen kopyalanır; sayfa sayısı ve sırası korunur.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable

import cv2
import numpy as np
import pymupdf
from PIL import Image

from .ocr import OcrEngine

ProgressCb = Callable[[float, str], None]

DPI = 300
_MERGE_DY = 4
_MERGE_GAP = 14
_MIN_SEGMENT = 26
_MAX_THICKNESS = 30
_MAX_WORDS_PER_LINE = 60


def _font_args() -> dict:
    windir = Path(os.environ.get("WINDIR", r"C:\Windows"))
    for name in ("arial.ttf", "segoeui.ttf", "calibri.ttf"):
        candidate = windir / "Fonts" / name
        if candidate.exists():
            return {"fontname": "pdf2-font", "fontfile": str(candidate)}
    return {"fontname": "helv"}


def _segments_from_mask(mask: np.ndarray, horizontal: bool) -> list[tuple]:
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    segments: list[tuple] = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if horizontal:
            if w < _MIN_SEGMENT or h > _MAX_THICKNESS:
                continue
            yc = y + h / 2
            segments.append((float(x), float(yc), float(x + w), float(yc)))
        else:
            if h < _MIN_SEGMENT or w > _MAX_THICKNESS:
                continue
            xc = x + w / 2
            segments.append((float(xc), float(y), float(xc), float(y + h)))
    return segments


def _merge_segments(segments: list[tuple], horizontal: bool) -> list[tuple]:
    if not segments:
        return []
    key_index = 1 if horizontal else 0
    segments = sorted(segments, key=lambda s: s[key_index])
    merged: list[tuple] = []
    for seg in segments:
        placed = False
        for i, current in enumerate(merged):
            if abs(seg[key_index] - current[key_index]) > _MERGE_DY:
                continue
            if horizontal:
                a0, a1 = current[0], current[2]
                b0, b1 = seg[0], seg[2]
            else:
                a0, a1 = current[1], current[3]
                b0, b1 = seg[1], seg[3]
            if min(a1, b1) + _MERGE_GAP < max(a0, b0):
                continue
            if horizontal:
                yc = (current[1] + seg[1]) / 2
                merged[i] = (min(a0, b0), yc, max(a1, b1), yc)
            else:
                xc = (current[0] + seg[0]) / 2
                merged[i] = (xc, min(a0, b0), xc, max(a1, b1))
            placed = True
            break
        if not placed:
            merged.append(seg)
    return merged


def detect_grid_lines(bgr: np.ndarray) -> tuple[list[tuple], list[tuple]]:
    """Görüntüdeki yatay ve dikey tablo kenarlıklarını piksel koordinatında döndürür."""
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY) if bgr.ndim == 3 else bgr
    binary = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 25, 12
    )
    height, width = binary.shape
    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(24, width // 50), 1))
    v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(24, height // 50)))
    horiz = cv2.morphologyEx(binary, cv2.MORPH_OPEN, h_kernel)
    vert = cv2.morphologyEx(binary, cv2.MORPH_OPEN, v_kernel)
    h_segments = _merge_segments(_segments_from_mask(horiz, True), True)
    v_segments = _merge_segments(_segments_from_mask(vert, False), False)
    return h_segments, v_segments


def _insert_word_layer(
    page: pymupdf.Page,
    lines: list[tuple[list[tuple[float, float]], str, float]],
    scale: float,
    font_args: dict,
) -> None:
    font = (
        pymupdf.Font(fontfile=font_args["fontfile"])
        if "fontfile" in font_args
        else pymupdf.Font("helv")
    )
    for points, text, _score in lines:
        text = text.strip()
        if not text:
            continue
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        x0, x1 = min(xs) * scale, max(xs) * scale
        y0, y1 = min(ys) * scale, max(ys) * scale
        box_height = y1 - y0
        if box_height < 3 or x1 <= x0:
            continue
        size = max(4.0, min(box_height * 0.72, 42.0))
        baseline = y1 - box_height * 0.16
        words = text.split()[:_MAX_WORDS_PER_LINE]
        if not words:
            continue
        total_width = font.text_length(" ".join(words), fontsize=size)
        if total_width <= 0:
            continue
        space_width = font.text_length(" ", fontsize=size)
        stretch = (x1 - x0) / total_width
        stretch = max(0.5, min(stretch, 2.5))
        x = x0
        for word in words:
            page.insert_text(
                (x, baseline),
                word,
                fontsize=size,
                color=(0.12, 0.12, 0.12),
                **font_args,
            )
            x += (font.text_length(word, fontsize=size) + space_width) * stretch


def build_searchable_pdf(
    src: str | Path,
    dst: str | Path,
    engine: OcrEngine,
    pages: list[int],
    lang: str = "tur+eng",
    dpi: int = DPI,
    progress: ProgressCb | None = None,
) -> dict:
    """Taranmış sayfaları görüntü + vektör çizgiler + görünmez metinle yeniden kurar."""
    source = pymupdf.open(str(src))
    out = pymupdf.open()
    targets = sorted(set(pages))
    target_set = set(targets)
    scale = 72.0 / dpi
    font_args = _font_args()
    rebuilt: list[int] = []

    try:
        for index in range(len(source)):
            if index not in target_set:
                out.insert_pdf(source, from_page=index, to_page=index)
                continue

            page = source[index]
            pix = page.get_pixmap(dpi=dpi, alpha=False)
            image = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                pix.height, pix.width, pix.n
            )
            if pix.n == 4:
                image = cv2.cvtColor(image, cv2.COLOR_RGBA2BGR)
            pil_image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

            new_page = out.new_page(
                width=pix.width * scale, height=pix.height * scale
            )

            h_segments, v_segments = detect_grid_lines(image)
            for x0, y0, x1, y1 in h_segments + v_segments:
                new_page.draw_line(
                    pymupdf.Point(x0 * scale, y0 * scale),
                    pymupdf.Point(x1 * scale, y1 * scale),
                    color=(0.3, 0.3, 0.3),
                    width=0.6,
                )

            lines = engine.recognize_lines(pil_image, lang)
            _insert_word_layer(new_page, lines, scale, font_args)
            rebuilt.append(index)

            if progress:
                fraction = 0.05 + 0.85 * len(rebuilt) / max(len(targets), 1)
                progress(fraction, f"OCR: sayfa {index + 1} ({engine.name})")

        out.save(str(dst), garbage=3, deflate=True)
    finally:
        out.close()
        source.close()
    return {"rebuilt_pages": rebuilt}
