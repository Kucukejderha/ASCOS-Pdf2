from __future__ import annotations

import pymupdf


def words_in_rect(page: pymupdf.Page, rect: pymupdf.Rect | tuple) -> list[tuple]:
    """Merkezi verilen dikdörtgenin içinde kalan kelimeleri döndürür."""
    rect = pymupdf.Rect(rect)
    words = page.get_text("words") or []
    selected = []
    for word in words:
        x0, y0, x1, y1 = word[:4]
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        if rect.x0 <= cx <= rect.x1 and rect.y0 <= cy <= rect.y1:
            selected.append(word)
    return selected


def extract_rect_text(page: pymupdf.Page, rect: pymupdf.Rect | tuple) -> str:
    """Dikdörtgen içindeki metni okuma sırasına göre birleştirir.

    Aynı satırdaki kelimeler boşlukla, farklı satırlar satır sonuyla ayrılır.
    """
    selected = words_in_rect(page, rect)
    if not selected:
        return ""
    selected.sort(key=lambda w: (w[5], w[6], w[7]))
    parts: list[str] = []
    current_line: tuple[int, int] | None = None
    for word in selected:
        line_key = (word[5], word[6])
        if current_line is not None and line_key != current_line:
            parts.append("\n")
        elif current_line is not None:
            parts.append(" ")
        parts.append(word[4])
        current_line = line_key
    return "".join(parts)


def span_at_point(page: pymupdf.Page, point: pymupdf.Point) -> dict | None:
    """Verilen noktadaki metin span'ini döndürür (punto, renk, font, bbox)."""
    data = page.get_text("dict") or {}
    for block in data.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                bbox = pymupdf.Rect(span.get("bbox", (0, 0, 0, 0)))
                if bbox.contains(point):
                    return span
    return None


def spans_in_rect(page: pymupdf.Page, rect: pymupdf.Rect | tuple) -> list[dict]:
    """Merkezi dikdörtgen içinde kalan span'ları okuma sırasına göre döndürür."""
    rect = pymupdf.Rect(rect)
    out: list[dict] = []
    data = page.get_text("dict") or {}
    for block in data.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                bbox = pymupdf.Rect(span.get("bbox", (0, 0, 0, 0)))
                cx, cy = (bbox.x0 + bbox.x1) / 2, (bbox.y0 + bbox.y1) / 2
                if rect.x0 <= cx <= rect.x1 and rect.y0 <= cy <= rect.y1:
                    out.append(span)
    out.sort(key=lambda s: (s["bbox"][1], s["bbox"][0]))
    return out
