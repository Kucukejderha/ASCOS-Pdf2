from __future__ import annotations

from pathlib import Path

from docx import Document


class WordDocumentEditor:
    """Word belgesinde paragraf ve tablo hücresi düzeyinde düzenleme.

    Metin değiştirilirken paragrafın ilk run'ının biçimi korunur; diğer
    run'lar temizlenir. Paragraf stili her durumda korunur.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.doc = Document(str(self.path))

    @property
    def paragraph_count(self) -> int:
        return len(self.doc.paragraphs)

    def paragraph_texts(self) -> list[str]:
        return [p.text for p in self.doc.paragraphs]

    def set_paragraph_text(self, index: int, text: str) -> None:
        paragraph = self.doc.paragraphs[index]
        if paragraph.runs:
            paragraph.runs[0].text = text
            for run in paragraph.runs[1:]:
                run.text = ""
        else:
            paragraph.add_run(text)

    @property
    def table_count(self) -> int:
        return len(self.doc.tables)

    def table_label(self, index: int) -> str:
        table = self.doc.tables[index]
        rows = len(table.rows)
        cols = len(table.columns)
        header = ""
        if table.rows and table.rows[0].cells:
            header = " | ".join(c.text.strip() for c in table.rows[0].cells[:4])
        return f"Tablo {index + 1} ({rows}×{cols}): {header}"

    def table_data(self, index: int) -> list[list[str]]:
        table = self.doc.tables[index]
        return [[cell.text for cell in row.cells] for row in table.rows]

    def set_table_cell(self, index: int, row: int, col: int, text: str) -> None:
        cell = self.doc.tables[index].rows[row].cells[col]
        if cell.paragraphs and cell.paragraphs[0].runs:
            first = cell.paragraphs[0]
            first.runs[0].text = text
            for run in first.runs[1:]:
                run.text = ""
        else:
            cell.text = text

    def save(self, dst: str | Path | None = None) -> Path:
        target = Path(dst) if dst else self.path
        target.parent.mkdir(parents=True, exist_ok=True)
        self.doc.save(str(target))
        return target
