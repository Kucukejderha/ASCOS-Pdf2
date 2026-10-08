from __future__ import annotations

import pymupdf

_TYPE_NAMES = {
    pymupdf.PDF_WIDGET_TYPE_TEXT: "Metin",
    pymupdf.PDF_WIDGET_TYPE_CHECKBOX: "Onay kutusu",
    pymupdf.PDF_WIDGET_TYPE_COMBOBOX: "Açılır liste",
    pymupdf.PDF_WIDGET_TYPE_LISTBOX: "Liste",
    pymupdf.PDF_WIDGET_TYPE_RADIOBUTTON: "Radyo düğmesi",
    pymupdf.PDF_WIDGET_TYPE_SIGNATURE: "İmza alanı",
}

_TRUTHY = {"1", "true", "evet", "yes", "x", "✓", "on"}


def _set_widget_value(widget: pymupdf.Widget, value) -> None:
    if widget.field_type == pymupdf.PDF_WIDGET_TYPE_CHECKBOX:
        widget.field_value = str(value).strip().lower() in _TRUTHY
    else:
        widget.field_value = str(value)


class FormMixin:
    """PdfEditSession ile birlikte kullanılır; self.doc, self.dirty ve self.snapshot bekler."""

    doc: pymupdf.Document
    dirty: bool

    def snapshot(self) -> None:  # PdfEditSession tarafından sağlanır
        raise NotImplementedError

    def list_form_fields(self) -> list[dict]:
        """Belgedeki form alanlarını listeler."""
        fields: list[dict] = []
        for page_index in range(len(self.doc)):
            page = self.doc[page_index]
            for widget in page.widgets() or []:
                fields.append(
                    {
                        "page": page_index,
                        "name": widget.field_name or f"alan_{page_index + 1}_{len(fields) + 1}",
                        "type": _TYPE_NAMES.get(widget.field_type, "Bilinmeyen"),
                        "value": widget.field_value,
                        "choices": list(widget.choice_values or []),
                    }
                )
        return fields

    def fill_form(self, values: dict) -> int:
        """Ad → değer eşlemesiyle form alanlarını doldurur; doldurulan alan sayısını döndürür."""
        if not values:
            return 0
        self.snapshot()
        count = 0
        for page in self.doc:
            for widget in page.widgets() or []:
                if widget.field_name in values:
                    _set_widget_value(widget, values[widget.field_name])
                    widget.update()
                    count += 1
        if count:
            self.dirty = True
        return count
