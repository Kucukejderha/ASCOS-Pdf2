from __future__ import annotations

from pathlib import Path

import pymupdf
import pytest

from app.core.pdf_editor.image_tools import fitted_rect
from app.core.pdf_editor.page_ops import (
    PdfEditSession,
    PdfPasswordError,
    merge_pdfs,
    split_pdf,
)


def _page_texts(path: Path) -> list[str]:
    with pymupdf.open(str(path)) as doc:
        return [page.get_text() for page in doc]


def test_rotate_move_delete_save(digital_pdf: Path, tmp_path: Path) -> None:
    session = PdfEditSession(digital_pdf)
    try:
        session.rotate(0, 90)
        assert session.doc[0].rotation == 90

        session.move(0, 1)
        out = tmp_path / "edited.pdf"
        session.save(out)
    finally:
        session.close()

    with pymupdf.open(str(out)) as doc:
        assert len(doc) == 2
        assert "IKINCI" in doc[0].get_text().upper()

    session = PdfEditSession(out)
    try:
        session.delete([0])
        session.save()
        assert session.page_count == 1
    finally:
        session.close()

    texts = _page_texts(out)
    assert "MERHABA" in texts[0].upper()
    assert "IKINCI" not in texts[0].upper()


def test_annotations_saved(digital_pdf: Path, tmp_path: Path) -> None:
    out = tmp_path / "annotated.pdf"
    session = PdfEditSession(digital_pdf)
    try:
        session.add_highlight(0, (72, 60, 300, 90))
        session.add_text(0, (72, 300), "Düzelti notu: Merhaba")
        session.add_note(0, (400, 60), "Buraya bak")
        session.save(out)
    finally:
        session.close()

    with pymupdf.open(str(out)) as doc:
        page = doc[0]
        annots = list(page.annots() or [])
        assert len(annots) >= 2
        text = page.get_text().replace("\xa0", " ")
        assert "Düzelti notu" in text


def test_split_and_merge(digital_pdf: Path, tmp_path: Path) -> None:
    parts = split_pdf(digital_pdf, tmp_path, "1;2")
    assert len(parts) == 2
    for part in parts:
        with pymupdf.open(str(part)) as doc:
            assert len(doc) == 1

    merged = tmp_path / "merged.pdf"
    merge_pdfs(parts, merged)
    with pymupdf.open(str(merged)) as doc:
        assert len(doc) == 2
        assert "MERHABA" in doc[0].get_text().upper()
        assert "IKINCI" in doc[1].get_text().upper()


def test_undo_redo_rotate(digital_pdf: Path) -> None:
    session = PdfEditSession(digital_pdf)
    try:
        assert not session.can_undo
        assert not session.can_redo

        session.rotate(0, 90)
        assert session.doc[0].rotation == 90
        assert session.can_undo

        assert session.undo() is True
        assert session.doc[0].rotation == 0
        assert session.can_redo

        assert session.redo() is True
        assert session.doc[0].rotation == 90
        assert not session.can_redo
    finally:
        session.close()


def test_undo_delete_and_redo_cleared_on_new_action(digital_pdf: Path) -> None:
    session = PdfEditSession(digital_pdf)
    try:
        session.delete([0])
        assert session.page_count == 1

        session.undo()
        assert session.page_count == 2

        session.redo()
        assert session.page_count == 1

        session.undo()
        assert session.page_count == 2

        session.rotate(0, 90)
        assert not session.can_redo

        assert session.redo() is False
        assert session.doc[0].rotation == 90
        assert session.page_count == 2
    finally:
        session.close()


def test_undo_stack_limit(digital_pdf: Path) -> None:
    session = PdfEditSession(digital_pdf)
    try:
        for _ in range(session.MAX_UNDO + 5):
            session.rotate(0, 90)
        undone = 0
        while session.undo():
            undone += 1
        assert undone == session.MAX_UNDO
    finally:
        session.close()


def test_undo_annotation(digital_pdf: Path) -> None:
    session = PdfEditSession(digital_pdf)
    try:
        session.add_text(0, (72, 300), "Gecici not")
        text = session.doc[0].get_text().replace("\xa0", " ")
        assert "Gecici" in text

        session.undo()
        assert "Gecici" not in session.doc[0].get_text()

        session.redo()
        text = session.doc[0].get_text().replace("\xa0", " ")
        assert "Gecici" in text
    finally:
        session.close()


def test_reload_clears_history(digital_pdf: Path) -> None:
    session = PdfEditSession(digital_pdf)
    try:
        session.rotate(0, 90)
        session.reload()
        assert not session.can_undo
        assert not session.can_redo
        assert session.doc[0].rotation == 0
    finally:
        session.close()


def test_whiten_keeps_text_and_adds_cover(digital_pdf: Path) -> None:
    session = PdfEditSession(digital_pdf)
    try:
        before = len(session.doc[0].get_drawings())
        session.whiten(0, (60, 55, 300, 80))
        after = len(session.doc[0].get_drawings())
        assert after > before
        assert "MERHABA" in session.doc[0].get_text().upper()
        assert session.can_undo
    finally:
        session.close()


def test_erase_content_removes_text_permanently(digital_pdf: Path, tmp_path: Path) -> None:
    out = tmp_path / "erased.pdf"
    session = PdfEditSession(digital_pdf)
    try:
        session.erase_content(0, (60, 55, 430, 80))
        text = session.doc[0].get_text().upper()
        assert "MERHABA" not in text
        assert "TEST BELGESIDIR" in text
        session.save(out)
    finally:
        session.close()

    with pymupdf.open(str(out)) as doc:
        assert "MERHABA" not in doc[0].get_text().upper()


def test_erase_content_undo_restores_text(digital_pdf: Path) -> None:
    session = PdfEditSession(digital_pdf)
    try:
        session.erase_content(0, (60, 55, 430, 80))
        assert "MERHABA" not in session.doc[0].get_text().upper()

        session.undo()
        assert "MERHABA" in session.doc[0].get_text().upper()
    finally:
        session.close()


def test_edit_text_replaces_and_keeps_size(digital_pdf: Path, tmp_path: Path) -> None:
    out = tmp_path / "edited.pdf"
    session = PdfEditSession(digital_pdf)
    try:
        session.edit_text(0, (60, 55, 430, 80), "YENI BASLIK")
        text = session.doc[0].get_text().replace("\xa0", " ").upper()
        assert "MERHABA" not in text
        assert "YENI BASLIK" in text
        assert "TEST BELGESIDIR" in text
        session.save(out)
    finally:
        session.close()

    with pymupdf.open(str(out)) as doc:
        data = doc[0].get_text("dict")
        sizes = [
            span["size"]
            for block in data["blocks"]
            if block.get("type") == 0
            for line in block["lines"]
            for span in line["spans"]
            if "YENI BASLIK" in span["text"].replace("\xa0", " ")
        ]
        assert sizes
        assert abs(sizes[0] - 12) < 0.5


def test_edit_text_undo_restores_original(digital_pdf: Path) -> None:
    session = PdfEditSession(digital_pdf)
    try:
        session.edit_text(0, (60, 55, 430, 80), "DEGISTI")
        assert "DEGISTI" in session.doc[0].get_text().upper()

        session.undo()
        text = session.doc[0].get_text().upper()
        assert "MERHABA" in text
        assert "DEGISTI" not in text
    finally:
        session.close()


def test_draw_shapes_and_save(digital_pdf: Path, tmp_path: Path) -> None:
    out = tmp_path / "drawn.pdf"
    session = PdfEditSession(digital_pdf)
    try:
        session.draw_rect(0, (300, 200, 400, 250), color=(1, 0, 0), width=2)
        session.draw_ellipse(0, (300, 260, 400, 310))
        session.draw_line(0, (300, 320), (400, 320))
        session.draw_arrow(0, (300, 340), (400, 360))
        session.draw_polyline(0, [(300, 380), (320, 390), (340, 375)])
        assert len(session.doc[0].get_drawings()) >= 5
        session.save(out)
    finally:
        session.close()

    with pymupdf.open(str(out)) as doc:
        assert len(doc[0].get_drawings()) >= 5


def test_draw_undo_removes_shape(digital_pdf: Path) -> None:
    session = PdfEditSession(digital_pdf)
    try:
        before = len(session.doc[0].get_drawings())
        session.draw_rect(0, (300, 200, 400, 250))
        assert len(session.doc[0].get_drawings()) == before + 1

        session.undo()
        assert len(session.doc[0].get_drawings()) == before
    finally:
        session.close()


def test_fitted_rect_keeps_aspect() -> None:
    rect = fitted_rect((0, 0, 200, 100), 100, 100)
    assert abs(rect.width - 100) < 0.01
    assert abs(rect.height - 100) < 0.01
    assert abs(rect.x0 - 50) < 0.01
    assert abs(rect.y0) < 0.01

    wide = fitted_rect((0, 0, 200, 100), 400, 100)
    assert abs(wide.width - 200) < 0.01
    assert abs(wide.height - 50) < 0.01
    assert abs(wide.y0 - 25) < 0.01


def test_insert_image_by_path(digital_pdf: Path, sample_png: Path, tmp_path: Path) -> None:
    out = tmp_path / "img.pdf"
    session = PdfEditSession(digital_pdf)
    before = 0
    try:
        before = len(session.doc[0].get_images())
        session.insert_image(0, (300, 400, 500, 500), path=str(sample_png))
        assert len(session.doc[0].get_images()) == before + 1
        session.save(out)
    finally:
        session.close()

    with pymupdf.open(str(out)) as doc:
        assert len(doc[0].get_images()) == before + 1


def test_insert_image_by_bytes_and_undo(digital_pdf: Path, sample_png: Path) -> None:
    session = PdfEditSession(digital_pdf)
    try:
        before = len(session.doc[0].get_images())
        session.insert_image(0, (300, 400, 500, 500), data=sample_png.read_bytes())
        assert len(session.doc[0].get_images()) == before + 1

        session.undo()
        assert len(session.doc[0].get_images()) == before
    finally:
        session.close()


def test_insert_image_requires_source(digital_pdf: Path) -> None:
    session = PdfEditSession(digital_pdf)
    try:
        with pytest.raises(ValueError):
            session.insert_image(0, (0, 0, 10, 10))
    finally:
        session.close()


def _norm(text: str) -> str:
    return text.replace("\xa0", " ")


def test_add_watermark_all_pages_and_undo(digital_pdf: Path) -> None:
    session = PdfEditSession(digital_pdf)
    try:
        session.add_watermark([0, 1], "TASLAK")
        for index in (0, 1):
            assert "TASLAK" in _norm(session.doc[index].get_text()).upper()

        session.undo()
        for index in (0, 1):
            assert "TASLAK" not in _norm(session.doc[index].get_text()).upper()
    finally:
        session.close()


def test_add_page_numbers_sequence(digital_pdf: Path) -> None:
    session = PdfEditSession(digital_pdf)
    try:
        session.add_page_numbers([0, 1])
        assert "Sayfa 1 / 2" in _norm(session.doc[0].get_text())
        assert "Sayfa 2 / 2" in _norm(session.doc[1].get_text())
    finally:
        session.close()


def test_add_page_numbers_selected_only_and_start(digital_pdf: Path) -> None:
    session = PdfEditSession(digital_pdf)
    try:
        session.add_page_numbers([1], start_number=5)
        assert "Sayfa 5 / 2" in _norm(session.doc[1].get_text())
        assert "Sayfa" not in _norm(session.doc[0].get_text())
    finally:
        session.close()


def test_reorder_pages_and_undo(digital_pdf: Path) -> None:
    session = PdfEditSession(digital_pdf)
    try:
        session.reorder([1, 0])
        assert "IKINCI" in session.doc[0].get_text().upper()
        assert "MERHABA" in session.doc[1].get_text().upper()

        session.undo()
        assert "MERHABA" in session.doc[0].get_text().upper()
    finally:
        session.close()


def test_duplicate_copy_paste_pages(digital_pdf: Path) -> None:
    session = PdfEditSession(digital_pdf)
    try:
        session.duplicate_pages([0])
        assert session.page_count == 3
        assert "MERHABA" in session.doc[0].get_text().upper()
        assert "MERHABA" in session.doc[1].get_text().upper()
        assert "IKINCI" in session.doc[2].get_text().upper()

        blobs = session.copy_pages([1])
        assert len(blobs) == 1
        session.paste_pages(blobs, at_index=0)
        assert session.page_count == 4
        assert "MERHABA" in session.doc[0].get_text().upper()

        session.undo()
        assert session.page_count == 3
        session.undo()
        assert session.page_count == 2
    finally:
        session.close()


def test_rotate_pages_batch_single_undo(digital_pdf: Path) -> None:
    session = PdfEditSession(digital_pdf)
    try:
        session.rotate_pages([0, 1], 90)
        assert session.doc[0].rotation == 90
        assert session.doc[1].rotation == 90

        session.undo()
        assert session.doc[0].rotation == 0
        assert session.doc[1].rotation == 0
    finally:
        session.close()


def test_set_crop_current_page_and_undo(digital_pdf: Path) -> None:
    session = PdfEditSession(digital_pdf)
    try:
        original0 = session.doc[0].rect
        original1 = session.doc[1].rect

        session.set_crop(0, (60, 60, 420, 300))
        assert session.doc[0].rect.width < original0.width
        assert abs(session.doc[1].rect.width - original1.width) < 0.01

        session.undo()
        assert abs(session.doc[0].rect.width - original0.width) < 0.01
    finally:
        session.close()


def test_set_crop_apply_all_and_persist(digital_pdf: Path, tmp_path: Path) -> None:
    out = tmp_path / "cropped.pdf"
    session = PdfEditSession(digital_pdf)
    try:
        session.set_crop(0, (50, 50, 300, 320), apply_to_all=True)
        assert session.doc[1].rect.width < 300
        session.save(out)
    finally:
        session.close()

    with pymupdf.open(str(out)) as doc:
        assert doc[0].rect.width < 300
        assert doc[1].rect.width < 300


def test_reset_crop_restores_full_page(digital_pdf: Path) -> None:
    session = PdfEditSession(digital_pdf)
    try:
        full = session.doc[0].rect
        session.set_crop(0, (60, 60, 420, 300))
        assert session.doc[0].rect.width < full.width

        session.reset_crop(page_index=0)
        assert abs(session.doc[0].rect.width - full.width) < 0.01
    finally:
        session.close()


def test_password_required_and_auth(encrypted_pdf: Path) -> None:
    with pytest.raises(PdfPasswordError):
        PdfEditSession(encrypted_pdf)

    with pytest.raises(PdfPasswordError):
        PdfEditSession(encrypted_pdf, password="yanlis")

    session = PdfEditSession(encrypted_pdf, password="gizli")
    try:
        assert "GIZLI" in session.doc[0].get_text().upper()
    finally:
        session.close()


def test_set_save_protection_roundtrip(digital_pdf: Path, tmp_path: Path) -> None:
    out = tmp_path / "korumali.pdf"
    session = PdfEditSession(digital_pdf)
    try:
        session.set_save_protection("abc123", allow_print=False, allow_copy=False)
        session.save(out)
    finally:
        session.close()

    with pymupdf.open(str(out)) as doc:
        assert doc.needs_pass
        assert doc.authenticate("abc123") > 0


def test_clear_save_protection(encrypted_pdf: Path, tmp_path: Path) -> None:
    out = tmp_path / "korumasiz.pdf"
    session = PdfEditSession(encrypted_pdf, password="gizli")
    try:
        session.clear_save_protection()
        session.save(out)
    finally:
        session.close()

    with pymupdf.open(str(out)) as doc:
        assert not doc.needs_pass


def test_form_fields_list_and_fill(form_pdf: Path, tmp_path: Path) -> None:
    out = tmp_path / "dolu.pdf"
    session = PdfEditSession(form_pdf)
    try:
        fields = session.list_form_fields()
        names = {f["name"] for f in fields}
        assert {"ad", "onay"} <= names

        count = session.fill_form({"ad": "Ali Veli", "onay": "Evet"})
        assert count == 2
        session.save(out)
    finally:
        session.close()

    with pymupdf.open(str(out)) as doc:
        values = {}
        for page in doc:
            for widget in page.widgets() or []:
                values[widget.field_name] = widget.field_value
    assert values.get("ad") == "Ali Veli"
    assert bool(values.get("onay")) is True
