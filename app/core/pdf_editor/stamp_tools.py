from __future__ import annotations

import pymupdf

from .annotate import _font_args


class StampMixin:
    """PdfEditSession ile birlikte kullanılır; self.doc, self.dirty ve self.snapshot bekler."""

    doc: pymupdf.Document
    dirty: bool

    def snapshot(self) -> None:  # PdfEditSession tarafından sağlanır
        raise NotImplementedError

    def add_watermark(
        self,
        pages: list[int],
        text: str,
        size: float = 48,
        color: tuple[float, float, float] = (0.71, 0.71, 0.71),
        opacity: float = 0.3,
        angle: float = 45,
    ) -> None:
        """Seçilen sayfalara ortalanmış, döndürülmüş filigran metni ekler."""
        if not text.strip() or not pages:
            return
        self.snapshot()
        for page_index in pages:
            page = self.doc[page_index]
            cx = page.rect.width / 2
            cy = page.rect.height / 2
            box = pymupdf.Rect(cx - 260, cy - size, cx + 260, cy + size)
            morph = (pymupdf.Point(cx, cy), pymupdf.Matrix(angle))
            page.insert_textbox(
                box,
                text,
                fontsize=size,
                color=color,
                fill_opacity=opacity,
                align=pymupdf.TEXT_ALIGN_CENTER,
                morph=morph,
                **_font_args(),
            )
        self.dirty = True

    def add_page_numbers(
        self,
        pages: list[int],
        template: str = "Sayfa {n} / {total}",
        size: float = 9,
        color: tuple[float, float, float] = (0.3, 0.3, 0.3),
        position: str = "bottom-center",
        start_number: int = 1,
        margin: float = 28,
    ) -> None:
        """Seçilen sayfalara sıralı sayfa numarası ekler."""
        if not pages:
            return
        self.snapshot()
        total = len(self.doc)
        box_height = size * 2.2
        for order, page_index in enumerate(pages):
            page = self.doc[page_index]
            number = start_number + order
            text = template.format(n=number, total=total)
            width = page.rect.width
            height = page.rect.height
            if position == "bottom-right":
                box = pymupdf.Rect(
                    width - 220 - margin,
                    height - margin - box_height,
                    width - margin,
                    height - margin,
                )
                align = pymupdf.TEXT_ALIGN_RIGHT
            elif position == "top-center":
                box = pymupdf.Rect(
                    margin, margin, width - margin, margin + box_height
                )
                align = pymupdf.TEXT_ALIGN_CENTER
            else:
                box = pymupdf.Rect(
                    margin,
                    height - margin - box_height,
                    width - margin,
                    height - margin,
                )
                align = pymupdf.TEXT_ALIGN_CENTER
            page.insert_textbox(
                box,
                text,
                fontsize=size,
                color=color,
                align=align,
                **_font_args(),
            )
        self.dirty = True
