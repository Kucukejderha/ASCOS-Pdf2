from __future__ import annotations

import io
from pathlib import Path

import pymupdf
import pytest
from PIL import Image, ImageDraw, ImageFont


def _insert_lines(page: pymupdf.Page, lines: list[str], x: float = 72, y: float = 72) -> None:
    for i, line in enumerate(lines):
        page.insert_text((x, y + i * 20), line, fontsize=12)


def _draw_table(
    page: pymupdf.Page,
    x: float,
    y: float,
    col_w: float,
    row_h: float,
    data: list[list[str]],
) -> None:
    rows, cols = len(data), len(data[0])
    for r in range(rows + 1):
        page.draw_line((x, y + r * row_h), (x + cols * col_w, y + r * row_h), color=(0, 0, 0), width=0.8)
    for c in range(cols + 1):
        page.draw_line((x + c * col_w, y), (x + c * col_w, y + rows * row_h), color=(0, 0, 0), width=0.8)
    for r in range(rows):
        for c in range(cols):
            page.insert_text((x + c * col_w + 4, y + r * row_h + 14), str(data[r][c]), fontsize=10)


def _text_image_bytes(
    text: str,
    size: tuple[int, int] = (1240, 400),
    text_xy: tuple[int, int] = (40, 150),
) -> bytes:
    img = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 64)
    except Exception:
        font = ImageFont.load_default(size=64)
    draw.text(text_xy, text, fill="black", font=font)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture(scope="session")
def digital_pdf(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("fixtures") / "digital.pdf"
    doc = pymupdf.open()
    page1 = doc.new_page(width=595, height=842)
    _insert_lines(page1, ["MERHABA DUNYA", "Bu bir test belgesidir.", "Pdf2 donusum testi."])
    _draw_table(
        page1,
        72,
        160,
        120,
        24,
        [["Urun", "Adet", "Fiyat"], ["Kalem", "3", "15,50"], ["Defter", "2", "42,75"]],
    )
    page2 = doc.new_page(width=595, height=842)
    _insert_lines(page2, ["IKINCI SAYFA", "Dijital metin iceriyor."])
    doc.save(str(path))
    doc.close()
    return path


@pytest.fixture(scope="session")
def scanned_pdf(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("fixtures") / "scanned.pdf"
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    img = _text_image_bytes("TARANMIS SAYFA", size=(1240, 1754), text_xy=(80, 750))
    page.insert_image(page.rect, stream=img)
    doc.save(str(path))
    doc.close()
    return path


@pytest.fixture(scope="session")
def mixed_pdf(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("fixtures") / "mixed.pdf"
    doc = pymupdf.open()
    page1 = doc.new_page(width=595, height=842)
    _insert_lines(page1, ["DIGITAL SAYFA", "Metin katmani var."])
    page2 = doc.new_page(width=595, height=842)
    img = _text_image_bytes("TARANMIS IKINCI SAYFA", size=(1240, 1754), text_xy=(80, 750))
    page2.insert_image(page2.rect, stream=img)
    doc.save(str(path))
    doc.close()
    return path


@pytest.fixture(scope="session")
def table4_pdf(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("fixtures") / "table4.pdf"
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((72, 80), "TEKLIF FORMU", fontsize=18)
    _draw_table(
        page,
        72,
        260,
        150,
        24,
        [
            ["Urun", "Adet", "Birim Fiyat", "Toplam"],
            ["Lisans", "2", "1250,00", "2500,00"],
            ["Destek", "12", "300,00", "3600,00"],
            ["Egitim", "1", "1750,00", "1750,00"],
        ],
    )
    doc.save(str(path))
    doc.close()
    return path


@pytest.fixture(scope="session")
def ocr_image() -> Image.Image:
    return Image.open(io.BytesIO(_text_image_bytes("TEST 123 PDF", size=(900, 300))))


@pytest.fixture(scope="session")
def sample_png(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("fixtures") / "imza.png"
    img = Image.new("RGBA", (240, 120), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 36)
    except Exception:
        font = ImageFont.load_default(size=36)
    draw.rectangle((4, 4, 236, 116), outline="black", width=2)
    draw.text((30, 40), "IMZA", fill="black", font=font)
    img.save(path)
    return path


@pytest.fixture(scope="session")
def encrypted_pdf(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("fixtures") / "encrypted.pdf"
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    _insert_lines(page, ["GIZLI BELGE", "Parola korumali icerik."])
    doc.save(
        str(path),
        encryption=pymupdf.PDF_ENCRYPT_AES_256,
        user_pw="gizli",
        owner_pw="gizli",
    )
    doc.close()
    return path


@pytest.fixture(scope="session")
def scanned_table_pdf(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Tablolu taranmış sayfa: yalnızca görüntü, metin katmanı yok."""
    path = tmp_path_factory.mktemp("fixtures") / "scanned_table.pdf"
    width, height = 1240, 1754
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 40)
    except Exception:
        font = ImageFont.load_default(size=40)
    x0, y0, cell_w, row_h = 120, 300, 250, 120
    rows = [
        ["URUN", "ADET", "FIYAT"],
        ["KALEM", "3", "15,50"],
        ["DEFTER", "2", "42,75"],
        ["TOPLAM", "", "140,75"],
    ]
    for r in range(len(rows) + 1):
        draw.line((x0, y0 + r * row_h, x0 + 3 * cell_w, y0 + r * row_h), fill="black", width=4)
    for c in range(4):
        draw.line((x0 + c * cell_w, y0, x0 + c * cell_w, y0 + len(rows) * row_h), fill="black", width=4)
    for r, row in enumerate(rows):
        for c, cell in enumerate(row):
            if cell:
                draw.text(
                    (x0 + c * cell_w + 15, y0 + r * row_h + 35),
                    cell,
                    fill="black",
                    font=font,
                )
    buf = io.BytesIO()
    img.save(buf, format="PNG")

    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    page.insert_image(page.rect, stream=buf.getvalue())
    doc.save(str(path))
    doc.close()
    return path


@pytest.fixture(scope="session")
def form_pdf(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("fixtures") / "form.pdf"
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    _insert_lines(page, ["FORM BELGESI"])

    text_widget = pymupdf.Widget()
    text_widget.field_name = "ad"
    text_widget.field_type = pymupdf.PDF_WIDGET_TYPE_TEXT
    text_widget.rect = pymupdf.Rect(72, 120, 320, 144)
    text_widget.field_value = ""
    page.add_widget(text_widget)

    check_widget = pymupdf.Widget()
    check_widget.field_name = "onay"
    check_widget.field_type = pymupdf.PDF_WIDGET_TYPE_CHECKBOX
    check_widget.rect = pymupdf.Rect(72, 160, 92, 180)
    check_widget.field_value = False
    page.add_widget(check_widget)

    doc.save(str(path))
    doc.close()
    return path
