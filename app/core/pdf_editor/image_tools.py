from __future__ import annotations

import pymupdf


def fitted_rect(
    rect: pymupdf.Rect | tuple, img_w: float, img_h: float
) -> pymupdf.Rect:
    """Görseli, verilen dikdörtgenin içine oranını koruyarak ortalar."""
    box = pymupdf.Rect(rect)
    if img_w <= 0 or img_h <= 0:
        return box
    scale = min(box.width / img_w, box.height / img_h)
    width = img_w * scale
    height = img_h * scale
    cx = (box.x0 + box.x1) / 2
    cy = (box.y0 + box.y1) / 2
    return pymupdf.Rect(cx - width / 2, cy - height / 2, cx + width / 2, cy + height / 2)


def image_size(*, path: str | None = None, data: bytes | None = None) -> tuple[int, int]:
    pix = pymupdf.Pixmap(str(path) if path else data)
    try:
        return pix.width, pix.height
    finally:
        del pix


class ImageMixin:
    """PdfEditSession ile birlikte kullanılır; self.doc, self.dirty ve self.snapshot bekler."""

    doc: pymupdf.Document
    dirty: bool

    def snapshot(self) -> None:  # PdfEditSession tarafından sağlanır
        raise NotImplementedError

    def insert_image(
        self,
        page_index: int,
        rect: tuple[float, float, float, float],
        *,
        path: str | None = None,
        data: bytes | None = None,
    ) -> None:
        """Görseli, oranını koruyarak verilen alana yerleştirir."""
        if path is None and data is None:
            raise ValueError("Görsel kaynağı belirtilmedi")
        width, height = image_size(path=path, data=data)
        target = fitted_rect(rect, width, height)

        self.snapshot()
        page = self.doc[page_index]
        if path is not None:
            page.insert_image(target, filename=str(path))
        else:
            page.insert_image(target, stream=data)
        self.dirty = True
