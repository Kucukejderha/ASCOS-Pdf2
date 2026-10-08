from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from app.core.utils import parse_page_range


class ConvertMode(str, Enum):
    WORD = "word"
    EXCEL = "excel"


class ExcelLayout(str, Enum):
    PAGE_PER_SHEET = "page_per_sheet"
    ALL_IN_ONE = "all_in_one"


@dataclass
class ConversionOptions:
    mode: ConvertMode = ConvertMode.WORD
    pages: str = ""
    ocr: bool = True
    ocr_lang: str = "tur+eng"
    ocr_engine: str = "auto"
    force_ocr: bool = False
    excel_layout: ExcelLayout = ExcelLayout.PAGE_PER_SHEET
    text_fallback: bool = True
    overwrite: bool = True

    def page_list(self, page_count: int) -> list[int] | None:
        selected = parse_page_range(self.pages, page_count)
        return selected


@dataclass
class PageAnalysis:
    number: int
    char_count: int
    image_area_ratio: float
    is_scanned: bool


@dataclass
class PdfAnalysis:
    page_count: int
    pages: list[PageAnalysis]

    @property
    def scanned_pages(self) -> list[int]:
        return [p.number for p in self.pages if p.is_scanned]

    @property
    def is_fully_scanned(self) -> bool:
        return bool(self.pages) and all(p.is_scanned for p in self.pages)

    @property
    def is_fully_digital(self) -> bool:
        return all(not p.is_scanned for p in self.pages)


@dataclass
class ConversionResult:
    source: Path
    output: Path
    mode: ConvertMode
    ocr_pages: list[int] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    elapsed_s: float = 0.0
