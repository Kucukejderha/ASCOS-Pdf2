from __future__ import annotations

import os
from pathlib import Path

import pymupdf

from app.core.utils import parse_page_range

from .text_tools import spans_in_rect


def _font_args() -> dict:
    windir = Path(os.environ.get("WINDIR", r"C:\Windows"))
    for name in ("arial.ttf", "segoeui.ttf", "calibri.ttf"):
        candidate = windir / "Fonts" / name
        if candidate.exists():
            return {"fontname": "pdf2-font", "fontfile": str(candidate)}
    return {"fontname": "helv"}


class AnnotationMixin:
    """PdfEditSession ile birlikte kullanılır; self.doc, self.dirty ve self.snapshot bekler."""

    doc: pymupdf.Document
    dirty: bool

    def snapshot(self) -> None:  # PdfEditSession tarafından sağlanır
        raise NotImplementedError

    def add_highlight(
        self,
        page_index: int,
        rect: tuple[float, float, float, float],
        color: tuple[float, float, float] = (1.0, 0.86, 0.28),
    ) -> None:
        self.snapshot()
        page = self.doc[page_index]
        annot = page.add_highlight_annot(pymupdf.Rect(rect))
        annot.set_colors(stroke=color)
        annot.update()
        self.dirty = True

    def add_text(
        self,
        page_index: int,
        point: tuple[float, float],
        text: str,
        size: float = 11,
        color: tuple[float, float, float] = (0.13, 0.14, 0.16),
    ) -> None:
        self.snapshot()
        page = self.doc[page_index]
        rect = pymupdf.Rect(point[0], point[1], page.rect.x1 - 24, page.rect.y1 - 24)
        remaining = page.insert_textbox(
            rect, text, fontsize=size, color=color, **_font_args()
        )
        if remaining < 0:
            raise ValueError("Metin sayfaya sığmadı")
        self.dirty = True

    def add_note(self, page_index: int, point: tuple[float, float], text: str) -> None:
        self.snapshot()
        page = self.doc[page_index]
        annot = page.add_text_annot(pymupdf.Point(point[0], point[1]), text)
        annot.set_info(title="Pdf2")
        annot.update()
        self.dirty = True

    def whiten(
        self,
        page_index: int,
        rect: tuple[float, float, float, float],
        color: tuple[float, float, float] = (1.0, 1.0, 1.0),
    ) -> None:
        """Alanın üstüne opak dikdörtgen çizer (görsel kapama)."""
        self.snapshot()
        page = self.doc[page_index]
        page.draw_rect(pymupdf.Rect(rect), color=color, fill=color, width=0)
        self.dirty = True

    def erase_content(
        self,
        page_index: int,
        rect: tuple[float, float, float, float],
        remove_images: bool = False,
    ) -> None:
        """Alanın altındaki metni (istenirse görselleri) kalıcı olarak kaldırır."""
        self.snapshot()
        page = self.doc[page_index]
        page.add_redact_annot(pymupdf.Rect(rect))
        page.apply_redactions(
            images=pymupdf.PDF_REDACT_IMAGE_REMOVE
            if remove_images
            else pymupdf.PDF_REDACT_IMAGE_NONE,
            text=pymupdf.PDF_REDACT_TEXT_REMOVE,
        )
        self.dirty = True

    def edit_text(
        self,
        page_index: int,
        rect: tuple[float, float, float, float],
        new_text: str,
    ) -> None:
        """Seçili alandaki metni silip yerine yenisini yazar.

        Punto ve renk, alandaki ilk span'dan alınır. Font birebir korunamaz;
        sistem yazı tipi (Arial) kullanılır. Çok satırlı alanda yeni metin ilk
        satırın konumuna yazılır.
        """
        self.snapshot()
        page = self.doc[page_index]
        box = pymupdf.Rect(rect)

        spans = spans_in_rect(page, box)
        size: float = 11.0
        color: tuple[float, float, float] = (0.13, 0.14, 0.16)
        origin: pymupdf.Point | None = None
        if spans:
            first = spans[0]
            size = float(first.get("size", 11.0))
            raw_color = int(first.get("color", 0))
            color = (
                ((raw_color >> 16) & 255) / 255,
                ((raw_color >> 8) & 255) / 255,
                (raw_color & 255) / 255,
            )
            if first.get("origin"):
                ox, oy = first["origin"]
                origin = pymupdf.Point(ox, oy)

        page.add_redact_annot(box)
        page.apply_redactions(
            images=pymupdf.PDF_REDACT_IMAGE_NONE,
            text=pymupdf.PDF_REDACT_TEXT_REMOVE,
        )

        if new_text.strip():
            if origin is None:
                origin = pymupdf.Point(box.x0, box.y1 - 2)
            page.insert_text(
                origin,
                new_text,
                fontsize=size,
                color=color,
                **_font_args(),
            )
        self.dirty = True
