from __future__ import annotations

import os
import re
from pathlib import Path

import pymupdf

from app.core.utils import parse_page_range, unique_path

from .annotate import AnnotationMixin
from .draw_tools import DrawingMixin
from .form_tools import FormMixin
from .image_tools import ImageMixin
from .stamp_tools import StampMixin


class PdfPasswordError(RuntimeError):
    """PDF parola korumalı ve parola verilmedi/yanlış."""


class PdfEditSession(AnnotationMixin, DrawingMixin, ImageMixin, StampMixin, FormMixin):
    """Açık bir PDF oturumu; değişiklikler bellekte tutulur, save() ile diske yazılır.

    Geri al/ileri al, her mutasyondan önce alınan bellek anlık görüntüleriyle
    (doc.tobytes) çalışır; en fazla MAX_UNDO adım saklanır.
    """

    MAX_UNDO = 20

    def __init__(self, path: str | Path, password: str | None = None) -> None:
        self.path = Path(path)
        self.doc = pymupdf.open(str(self.path))
        if self.doc.needs_pass:
            if not password or not self.doc.authenticate(password):
                self.doc.close()
                raise PdfPasswordError("PDF parola korumalı; doğru parola gerekli")
            self.password = password
        self.dirty = False
        self._undo_stack: list[bytes] = []
        self._redo_stack: list[bytes] = []
        self._save_encryption: dict | None = None

    @property
    def page_count(self) -> int:
        return len(self.doc)

    def _snapshot_bytes(self) -> bytes:
        return self.doc.tobytes(garbage=3, deflate=True)

    def snapshot(self) -> None:
        """Her mutasyondan ÖNCE çağrılır; mevcut durumu geri al yığınına iter."""
        self._undo_stack.append(self._snapshot_bytes())
        if len(self._undo_stack) > self.MAX_UNDO:
            self._undo_stack.pop(0)
        self._redo_stack.clear()

    @property
    def can_undo(self) -> bool:
        return bool(self._undo_stack)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo_stack)

    def _replace_doc(self, data: bytes) -> None:
        self.doc.close()
        self.doc = pymupdf.open(stream=data, filetype="pdf")

    def undo(self) -> bool:
        if not self._undo_stack:
            return False
        self._redo_stack.append(self._snapshot_bytes())
        if len(self._redo_stack) > self.MAX_UNDO:
            self._redo_stack.pop(0)
        self._replace_doc(self._undo_stack.pop())
        self.dirty = True
        return True

    def redo(self) -> bool:
        if not self._redo_stack:
            return False
        self._undo_stack.append(self._snapshot_bytes())
        if len(self._undo_stack) > self.MAX_UNDO:
            self._undo_stack.pop(0)
        self._replace_doc(self._redo_stack.pop())
        self.dirty = True
        return True

    def clear_history(self) -> None:
        self._undo_stack.clear()
        self._redo_stack.clear()

    def rotate(self, page_index: int, delta: int) -> None:
        self.rotate_pages([page_index], delta)

    def rotate_pages(self, indexes: list[int], delta: int) -> None:
        if not indexes:
            return
        self.snapshot()
        for index in indexes:
            page = self.doc[index]
            page.set_rotation((page.rotation + delta) % 360)
        self.dirty = True

    def delete(self, indexes: list[int]) -> None:
        self.snapshot()
        self.doc.delete_pages(indexes)
        self.dirty = True

    def move(self, from_index: int, to_index: int) -> None:
        self.snapshot()
        order = list(range(len(self.doc)))
        item = order.pop(from_index)
        order.insert(max(0, min(to_index, len(order))), item)
        self.doc.select(order)
        self.dirty = True

    def reorder(self, order: list[int]) -> None:
        """Sayfaları verilen sıraya göre yeniden dizer."""
        if sorted(order) != list(range(len(self.doc))):
            raise ValueError("Sıralama tüm sayfaları içermeli")
        self.snapshot()
        self.doc.select(order)
        self.dirty = True

    def duplicate_pages(self, indexes: list[int]) -> None:
        """Seçili sayfaları kendi konumlarının hemen ardına kopyalar."""
        if not indexes:
            return
        self.snapshot()
        for index in sorted(indexes, reverse=True):
            copy = pymupdf.open()
            try:
                copy.insert_pdf(self.doc, from_page=index, to_page=index)
                self.doc.insert_pdf(copy, start_at=index + 1)
            finally:
                copy.close()
        self.dirty = True

    def copy_pages(self, indexes: list[int]) -> list[bytes]:
        """Seçili sayfaların tek sayfalık PDF bayt kopyalarını döndürür."""
        blobs: list[bytes] = []
        for index in indexes:
            part = pymupdf.open()
            try:
                part.insert_pdf(self.doc, from_page=index, to_page=index)
                blobs.append(part.tobytes(garbage=3, deflate=True))
            finally:
                part.close()
        return blobs

    def paste_pages(self, blobs: list[bytes], at_index: int) -> None:
        """Bayt kopyalarını verilen konumdan itibaren belgeye ekler."""
        if not blobs:
            return
        self.snapshot()
        position = max(0, min(at_index, len(self.doc)))
        for blob in blobs:
            part = pymupdf.open(stream=blob, filetype="pdf")
            try:
                self.doc.insert_pdf(part, start_at=position)
            finally:
                part.close()
            position += 1
        self.dirty = True

    def insert_from(self, other: str | Path, at_index: int | None = None) -> None:
        self.snapshot()
        with pymupdf.open(str(other)) as src:
            if at_index is None:
                self.doc.insert_pdf(src)
            else:
                self.doc.insert_pdf(src, start_at=at_index)
        self.dirty = True

    def render(self, page_index: int, zoom: float = 1.5) -> bytes:
        page = self.doc[page_index]
        matrix = pymupdf.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        return pix.tobytes("png")

    def render_thumbnail(self, page_index: int, width: int = 96) -> bytes:
        page = self.doc[page_index]
        zoom = width / page.rect.width if page.rect.width else 0.2
        matrix = pymupdf.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        return pix.tobytes("png")

    def set_crop(
        self,
        page_index: int,
        rect: tuple[float, float, float, float],
        apply_to_all: bool = False,
    ) -> None:
        """Görünür alanı (CropBox) verilen dikdörtgene daraltır."""
        self.snapshot()
        targets = range(len(self.doc)) if apply_to_all else [page_index]
        box = pymupdf.Rect(rect)
        for index in targets:
            self.doc[index].set_cropbox(box)
        self.dirty = True

    def reset_crop(self, apply_to_all: bool = False, page_index: int = 0) -> None:
        """Kırpmayı kaldırır; sayfanın tamamı yeniden görünür olur."""
        self.snapshot()
        targets = range(len(self.doc)) if apply_to_all else [page_index]
        for index in targets:
            page = self.doc[index]
            page.set_cropbox(page.mediabox)
        self.dirty = True

    def set_save_protection(
        self,
        user_password: str,
        owner_password: str | None = None,
        allow_print: bool = True,
        allow_copy: bool = True,
    ) -> None:
        """Sonraki kayıtlarda uygulanacak şifreleme ayarlarını belirler."""
        permissions = pymupdf.PDF_PERM_ACCESSIBILITY
        if allow_print:
            permissions |= pymupdf.PDF_PERM_PRINT
        if allow_copy:
            permissions |= pymupdf.PDF_PERM_COPY
        self._save_encryption = {
            "encryption": pymupdf.PDF_ENCRYPT_AES_256,
            "user_pw": user_password,
            "owner_pw": owner_password or user_password,
            "permissions": permissions,
        }
        self.dirty = True

    def clear_save_protection(self) -> None:
        """Sonraki kayıtta şifre korumasını kaldırır."""
        self._save_encryption = {"encryption": pymupdf.PDF_ENCRYPT_NONE}
        self.dirty = True

    def _save_kwargs(self) -> dict:
        kwargs = {"garbage": 3, "deflate": True}
        if self._save_encryption:
            kwargs.update(self._save_encryption)
        return kwargs

    def save(self, dst: str | Path | None = None) -> Path:
        target = Path(dst) if dst else self.path
        target.parent.mkdir(parents=True, exist_ok=True)
        kwargs = self._save_kwargs()
        if target == self.path:
            tmp = self.path.with_name(self.path.stem + ".pdf2_tmp.pdf")
            self.doc.save(str(tmp), **kwargs)
            self.doc.close()
            os.replace(tmp, self.path)
            self.doc = pymupdf.open(str(self.path))
            if self._save_encryption and self._save_encryption.get("user_pw"):
                self.doc.authenticate(self._save_encryption["user_pw"])
        else:
            self.doc.save(str(target), **kwargs)
        self.dirty = False
        return target

    def reload(self) -> None:
        self.doc.close()
        self.doc = pymupdf.open(str(self.path))
        self.dirty = False
        self.clear_history()

    def close(self) -> None:
        self.doc.close()


def merge_pdfs(paths: list[str | Path], dst: str | Path) -> Path:
    dst = Path(dst)
    out = pymupdf.open()
    try:
        for path in paths:
            with pymupdf.open(str(path)) as src:
                out.insert_pdf(src)
        dst.parent.mkdir(parents=True, exist_ok=True)
        out.save(str(dst), garbage=3, deflate=True)
    finally:
        out.close()
    return dst


def split_pdf(src: str | Path, out_dir: str | Path, ranges_text: str) -> list[Path]:
    src = Path(src)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    groups = [g.strip() for g in re.split(r"[;,]", ranges_text) if g.strip()]
    if not groups:
        raise ValueError("Bölme aralığı boş")
    outputs: list[Path] = []
    doc = pymupdf.open(str(src))
    try:
        for i, group in enumerate(groups):
            pages = parse_page_range(group, len(doc))
            if not pages:
                continue
            part = pymupdf.open()
            try:
                for p in pages:
                    part.insert_pdf(doc, from_page=p, to_page=p)
                dst = unique_path(out_dir / f"{src.stem}_bolum{i + 1}.pdf")
                part.save(str(dst), garbage=3, deflate=True)
                outputs.append(dst)
            finally:
                part.close()
    finally:
        doc.close()
    return outputs
