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
_MIN_SEGMENT = 20
_MAX_THICKNESS = 40
_MAX_WORDS_PER_LINE = 60


def _deskew_image(image: np.ndarray) -> np.ndarray:
    """Normalize obvious 90-degree scan rotations before OCR/line detection.

    PCA tek başına güvenilir değildir (normal metin sayfalarını da döndürebilir);
    bu nedenle yalnızca "hiç yatay çizgi yok, dikey çizgi var" gibi güçlü
    kanıtda 90° döndürme uygulanır.
    """
    if image.ndim == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    foreground = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    ys, xs = np.where(foreground > 0)
    if len(xs) < 100:
        return image
    # Use the long axis of foreground pixels; blank page margins do not affect it.
    points = np.column_stack((xs, ys)).astype(np.float32)
    _, vectors = cv2.PCACompute(points, mean=None, maxComponents=2)
    axis = vectors[0]
    angle = abs(float(np.degrees(np.arctan2(axis[1], axis[0])))) % 180
    if not (70 <= angle <= 110):
        return image

    sample = image
    height, width = image.shape[:2]
    if max(height, width) > 1600:
        sample = cv2.resize(
            image, (width // 2, height // 2), interpolation=cv2.INTER_AREA
        )
    h_lines, v_lines = detect_grid_lines(sample)
    if len(h_lines) == 0 and len(v_lines) >= 2:
        return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
    return image


def _cluster_positions(values: list[float], tolerance: float) -> list[float]:
    if not values:
        return []
    ordered = sorted(values)
    groups: list[list[float]] = [[ordered[0]]]
    for value in ordered[1:]:
        if value - groups[-1][-1] <= tolerance:
            groups[-1].append(value)
        else:
            groups.append([value])
    return [sum(group) / len(group) for group in groups]


def detect_table_grid(
    bgr: np.ndarray,
) -> tuple[list[float], list[float]]:
    """Return major table grid x/y coordinates in image pixels.

    Yatay çizgiler satır sınırlarını verir. Dikey çizgi anlamlı sayıdaysa
    sütunlar onlardan, değilse (yalnız yatay çizgili tablolar) sütunlar OCR
    kutu kümelerinden çıkarılır; bu durumda xs boş döner ve çağıran taraf
    metin-kümeleme yedeğini kullanır.
    """
    horizontal, vertical = detect_grid_lines(bgr)
    height, width = bgr.shape[:2]
    ys = _cluster_positions([s[1] for s in horizontal], max(4, height * 0.006))
    xs = _cluster_positions([s[0] for s in vertical], max(4, width * 0.006))

    # Uzun yatay kuralları olan satırları tut (kısa alt çizgileri ele).
    def row_supported(y: float) -> bool:
        for x0, y0, x1, _ in horizontal:
            if abs(y - y0) <= max(5, height * 0.008):
                if (x1 - x0) >= max(80.0, width * 0.15):
                    return True
        return False

    ys = [y for y in ys if row_supported(y)]
    if len(ys) < 2:
        return [], []
    if len(xs) < 2:
        return [], ys

    # Grid crossings: destek matrisi; gerçek kesişimler 2 destek alır.
    support = np.zeros((len(ys), len(xs)), dtype=np.int32)
    for yi, y in enumerate(ys):
        for xi, x in enumerate(xs):
            for x0, y0, x1, _ in horizontal:
                if abs(y - y0) <= max(5, height * 0.008) and x0 - 6 <= x <= x1 + 6:
                    support[yi, xi] += 1
                    break
            for x0, y0, _, y1 in vertical:
                if abs(x - x0) <= max(5, width * 0.008) and y0 - 6 <= y <= y1 + 6:
                    support[yi, xi] += 1
                    break
    active_rows = [i for i, row in enumerate(support) if int(row.sum()) >= 2]
    active_cols = [i for i in range(len(xs)) if int(support[:, i].sum()) >= 2]
    if len(active_rows) < 2 or len(active_cols) < 2:
        return [], ys
    y0, y1 = min(active_rows), max(active_rows)
    x0, x1 = min(active_cols), max(active_cols)
    return xs[x0 : x1 + 1], ys[y0 : y1 + 1]


def _map_lines_to_grid(
    lines: list[tuple[list[tuple[float, float]], str, float]],
    xs: list[float],
    ys: list[float],
) -> list[list[str]]:
    table = [["" for _ in range(len(xs) - 1)] for _ in range(len(ys) - 1)]
    assigned: list[list[list[tuple[float, str]]]] = [
        [[] for _ in range(len(xs) - 1)] for _ in range(len(ys) - 1)
    ]
    for points, text, score in lines:
        if not text.strip() or score < 0.08:
            continue
        cx = sum(point[0] for point in points) / len(points)
        cy = sum(point[1] for point in points) / len(points)
        col = int(np.searchsorted(xs, cx, side="right") - 1)
        row = int(np.searchsorted(ys, cy, side="right") - 1)
        if 0 <= row < len(assigned) and 0 <= col < len(assigned[row]):
            assigned[row][col].append((cy, text.strip()))
    for r, row in enumerate(assigned):
        for c, items in enumerate(row):
            table[r][c] = " ".join(text for _, text in sorted(items))
    while table and not any(cell for cell in table[0]):
        table.pop(0)
    while table and not any(cell for cell in table[-1]):
        table.pop()
    return table


def _table_from_text_clusters(
    lines: list[tuple[list[tuple[float, float]], str, float]],
    width: int,
    height: int,
) -> list[list[str]]:
    """Çizgisiz/yalnız yatay çizgili tablolar için OCR kutularından ızgara kurar.

    Sütunlar x-aralıklarının boşluk kümelenmesinden, satırlar y-merkezlerinin
    kümelenmesinden çıkarılır. Düz metin sayfalarında sütun oluşmadığı için boş
    liste döner (yanlış tablo üretilmez).
    """
    boxes: list[tuple[float, float, float, float, str]] = []
    for points, text, score in lines:
        text = text.strip()
        if not text or score < 0.08:
            continue
        xs_ = [p[0] for p in points]
        ys_ = [p[1] for p in points]
        boxes.append((min(xs_), min(ys_), max(xs_), max(ys_), text))
    if len(boxes) < 4:
        return []

    heights = [b[3] - b[1] for b in boxes if b[3] > b[1]]
    median_height = float(np.median(heights)) if heights else 20.0
    row_tolerance = max(10.0, median_height * 0.7)

    rows: list[list] = []
    for box in sorted(boxes, key=lambda b: (b[1] + b[3]) / 2):
        cy = (box[1] + box[3]) / 2
        for row in rows:
            if abs(row[0] - cy) <= row_tolerance:
                row[1].append(box)
                row[0] = sum((b[1] + b[3]) / 2 for b in row[1]) / len(row[1])
                break
        else:
            rows.append([cy, [box]])
    if len(rows) < 2:
        return []

    gap_min = max(30.0, width * 0.03)
    columns: list[list[float]] = []
    for x0, x1 in sorted((b[0], b[2]) for b in boxes):
        if columns and x0 - columns[-1][1] <= gap_min:
            columns[-1][1] = max(columns[-1][1], x1)
        else:
            columns.append([x0, x1])
    if len(columns) < 2:
        return []

    bounds = [c[0] for c in columns] + [columns[-1][1]]
    table = [["" for _ in columns] for _ in rows]
    for r_idx, (_, row_boxes) in enumerate(sorted(rows, key=lambda r: r[0])):
        for box in row_boxes:
            cx = (box[0] + box[2]) / 2
            c_idx = int(np.searchsorted(bounds, cx, side="right") - 1)
            c_idx = max(0, min(c_idx, len(columns) - 1))
            table[r_idx][c_idx] = (table[r_idx][c_idx] + " " + box[4]).strip()

    while table and not any(table[0]):
        table.pop(0)
    while table and not any(table[-1]):
        table.pop()
    if not table:
        return []
    keep = [c for c in range(len(table[0])) if any(row[c] for row in table)]
    if len(keep) < 2:
        return []
    return [[row[c] for c in keep] for row in table]


def extract_ocr_table(
    image: Image.Image,
    engine: OcrEngine,
    lang: str = "tur+eng",
) -> list[list[str]]:
    """OCR kutularını çizgili/çizgisiz tablonun hücrelerine eşler."""
    pixels = cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)
    pixels = _deskew_image(pixels)
    lines = engine.recognize_lines(
        Image.fromarray(cv2.cvtColor(pixels, cv2.COLOR_BGR2RGB)), lang
    )

    xs, ys = detect_table_grid(pixels)
    if len(xs) >= 2 and len(ys) >= 2:
        table = _map_lines_to_grid(lines, xs, ys)
        if table:
            return table
    return _table_from_text_clusters(lines, pixels.shape[1], pixels.shape[0])


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
    """Görüntüdeki yatay ve dikey tablo kenarlıklarını piksel koordinatında döndürür.

    Soluk/ince çizgilerin kaçmaması için adaptif ve Otsu maskeleri birleştirilir.
    """
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY) if bgr.ndim == 3 else bgr
    adaptive = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 25, 12
    )
    _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    binary = cv2.bitwise_or(adaptive, otsu)
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
