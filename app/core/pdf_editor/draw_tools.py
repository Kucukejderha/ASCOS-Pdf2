from __future__ import annotations

import math

import pymupdf


class DrawingMixin:
    """PdfEditSession ile birlikte kullanılır; self.doc, self.dirty ve self.snapshot bekler."""

    doc: pymupdf.Document
    dirty: bool

    def snapshot(self) -> None:  # PdfEditSession tarafından sağlanır
        raise NotImplementedError

    def _commit_shape(self, shape: pymupdf.Shape) -> None:
        shape.commit()
        self.dirty = True

    def draw_rect(
        self,
        page_index: int,
        rect: tuple[float, float, float, float],
        color: tuple[float, float, float] = (0.13, 0.14, 0.16),
        width: float = 1.5,
    ) -> None:
        self.snapshot()
        page = self.doc[page_index]
        shape = page.new_shape()
        shape.draw_rect(pymupdf.Rect(rect))
        shape.finish(color=color, width=width)
        self._commit_shape(shape)

    def draw_ellipse(
        self,
        page_index: int,
        rect: tuple[float, float, float, float],
        color: tuple[float, float, float] = (0.13, 0.14, 0.16),
        width: float = 1.5,
    ) -> None:
        self.snapshot()
        page = self.doc[page_index]
        shape = page.new_shape()
        shape.draw_oval(pymupdf.Rect(rect))
        shape.finish(color=color, width=width)
        self._commit_shape(shape)

    def draw_line(
        self,
        page_index: int,
        start: tuple[float, float],
        end: tuple[float, float],
        color: tuple[float, float, float] = (0.13, 0.14, 0.16),
        width: float = 1.5,
    ) -> None:
        self.snapshot()
        page = self.doc[page_index]
        shape = page.new_shape()
        shape.draw_line(pymupdf.Point(start), pymupdf.Point(end))
        shape.finish(color=color, width=width)
        self._commit_shape(shape)

    def draw_arrow(
        self,
        page_index: int,
        start: tuple[float, float],
        end: tuple[float, float],
        color: tuple[float, float, float] = (0.13, 0.14, 0.16),
        width: float = 1.5,
    ) -> None:
        self.snapshot()
        page = self.doc[page_index]
        x0, y0 = start
        x1, y1 = end
        dx, dy = x1 - x0, y1 - y0
        length = math.hypot(dx, dy)
        if length < 1:
            return
        head = max(8.0, width * 4)
        angle = math.atan2(dy, dx)
        wing = math.radians(25)
        p1 = (x1 - head * math.cos(angle - wing), y1 - head * math.sin(angle - wing))
        p2 = (x1 - head * math.cos(angle + wing), y1 - head * math.sin(angle + wing))
        shape = page.new_shape()
        shape.draw_line(pymupdf.Point(x0, y0), pymupdf.Point(x1, y1))
        shape.draw_line(pymupdf.Point(x1, y1), pymupdf.Point(*p1))
        shape.draw_line(pymupdf.Point(x1, y1), pymupdf.Point(*p2))
        shape.finish(color=color, width=width)
        self._commit_shape(shape)

    def draw_polyline(
        self,
        page_index: int,
        points: list[tuple[float, float]],
        color: tuple[float, float, float] = (0.13, 0.14, 0.16),
        width: float = 1.5,
    ) -> None:
        if len(points) < 2:
            return
        self.snapshot()
        page = self.doc[page_index]
        shape = page.new_shape()
        shape.draw_polyline([pymupdf.Point(p) for p in points])
        shape.finish(color=color, width=width, closePath=False)
        self._commit_shape(shape)
