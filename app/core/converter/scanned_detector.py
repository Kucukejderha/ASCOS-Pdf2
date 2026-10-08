from __future__ import annotations

from pathlib import Path

import pymupdf

from app.core.models import PageAnalysis, PdfAnalysis

MIN_TEXT_CHARS = 50
MIN_IMAGE_AREA_RATIO = 0.30


def analyze_page(page: pymupdf.Page, number: int) -> PageAnalysis:
    text = page.get_text("text") or ""
    char_count = sum(1 for c in text if c.isalnum())

    page_area = abs(page.rect.width * page.rect.height) or 1.0
    image_area = 0.0
    try:
        for info in page.get_image_info():
            bbox = info.get("bbox")
            if bbox:
                r = pymupdf.Rect(bbox)
                image_area += abs(r.width * r.height)
    except Exception:
        pass
    image_area_ratio = min(image_area / page_area, 1.0)

    is_scanned = char_count < MIN_TEXT_CHARS and image_area_ratio >= MIN_IMAGE_AREA_RATIO
    return PageAnalysis(
        number=number,
        char_count=char_count,
        image_area_ratio=image_area_ratio,
        is_scanned=is_scanned,
    )


def analyze_pdf(path: str | Path, max_pages: int | None = None) -> PdfAnalysis:
    with pymupdf.open(str(path)) as doc:
        count = len(doc)
        limit = min(count, max_pages) if max_pages else count
        pages = [analyze_page(doc[i], i) for i in range(limit)]
    return PdfAnalysis(page_count=count, pages=pages)
