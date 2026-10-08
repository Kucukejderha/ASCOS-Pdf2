from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from openpyxl.utils import get_column_letter

from app.core.output_editor.excel_editor import ExcelWorkbookEditor
from app.core.output_editor.word_editor import WordDocumentEditor

UI_MAX_ROWS = 400
UI_MAX_COLS = 60


def _readonly_item(text: str) -> QTableWidgetItem:
    item = QTableWidgetItem(text)
    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
    return item


class OutputEditorTab(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.word_editor: WordDocumentEditor | None = None
        self.excel_editor: ExcelWorkbookEditor | None = None
        self._loading = False
        self._dirty = False
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(10)

        toolbar = QFrame()
        toolbar.setObjectName("Panel")
        bar = QHBoxLayout(toolbar)
        bar.setContentsMargins(12, 8, 12, 8)
        bar.setSpacing(8)

        self.open_button = QPushButton("Belge aç…")
        self.open_button.setToolTip("Word (.docx) veya Excel (.xlsx) dosyası açın")
        self.open_button.clicked.connect(self._open_dialog)
        bar.addWidget(self.open_button)

        self.file_label = QLabel("Belge açılmadı")
        self.file_label.setObjectName("Muted")
        bar.addWidget(self.file_label)

        self.dirty_label = QLabel("kaydedilmedi")
        self.dirty_label.setStyleSheet("color: #B3372A;")
        self.dirty_label.setVisible(False)
        bar.addWidget(self.dirty_label)

        bar.addSpacing(10)
        self.table_label = QLabel("Tablo")
        bar.addWidget(self.table_label)
        self.table_combo = QComboBox()
        self.table_combo.setMinimumWidth(260)
        self.table_combo.currentIndexChanged.connect(self._table_changed)
        bar.addWidget(self.table_combo)

        self.sheet_label = QLabel("Sayfa")
        bar.addWidget(self.sheet_label)
        self.sheet_combo = QComboBox()
        self.sheet_combo.setMinimumWidth(160)
        self.sheet_combo.currentIndexChanged.connect(self._sheet_changed)
        bar.addWidget(self.sheet_combo)

        bar.addStretch(1)
        self.system_button = QPushButton("Uygulamada aç")
        self.system_button.setToolTip("Dosyayı Word/Excel ile aç")
        self.system_button.clicked.connect(self._open_in_system)
        bar.addWidget(self.system_button)
        self.save_as_button = QPushButton("Farklı kaydet…")
        self.save_as_button.setObjectName("Ghost")
        self.save_as_button.clicked.connect(self._save_as)
        bar.addWidget(self.save_as_button)
        self.save_button = QPushButton("Kaydet")
        self.save_button.setObjectName("Primary")
        self.save_button.clicked.connect(self._save)
        bar.addWidget(self.save_button)
        root.addWidget(toolbar)

        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_empty_page())
        self.stack.addWidget(self._build_word_page())
        self.stack.addWidget(self._build_excel_page())
        root.addWidget(self.stack, 1)

        self.status = QLabel("")
        self.status.setObjectName("Muted")
        root.addWidget(self.status)

        self._set_controls_enabled(False)

    def _build_empty_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addStretch(1)
        message = QLabel(
            "Word (.docx) veya Excel (.xlsx) dosyası açın.\n"
            "Dönüştür sekmesinde üretilen çıktılar ya da dışarıdan gelen belgeler düzenlenebilir."
        )
        message.setObjectName("Muted")
        message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(message)
        layout.addStretch(1)
        return page

    def _build_word_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Vertical)

        top_panel = QFrame()
        top_panel.setObjectName("Panel")
        top = QVBoxLayout(top_panel)
        top.setContentsMargins(12, 10, 12, 10)
        top.setSpacing(6)
        top_title = QLabel("Paragraflar")
        top_title.setObjectName("PanelTitle")
        top.addWidget(top_title)
        self.paragraph_list = QListWidget()
        self.paragraph_list.itemDoubleClicked.connect(self._edit_paragraph)
        top.addWidget(self.paragraph_list, 1)
        hint = QLabel("Düzenlemek için paragrafa çift tıklayın")
        hint.setObjectName("Muted")
        top.addWidget(hint)
        splitter.addWidget(top_panel)

        bottom_panel = QFrame()
        bottom_panel.setObjectName("Panel")
        bottom = QVBoxLayout(bottom_panel)
        bottom.setContentsMargins(12, 10, 12, 10)
        bottom.setSpacing(6)
        self.word_table_grid = QTableWidget()
        self.word_table_grid.itemChanged.connect(self._word_cell_changed)
        bottom.addWidget(self.word_table_grid, 1)
        splitter.addWidget(bottom_panel)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)
        layout.addWidget(splitter)
        return page

    def _build_excel_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        panel = QFrame()
        panel.setObjectName("Panel")
        inner = QVBoxLayout(panel)
        inner.setContentsMargins(12, 10, 12, 10)
        self.excel_grid = QTableWidget()
        self.excel_grid.itemChanged.connect(self._excel_cell_changed)
        inner.addWidget(self.excel_grid, 1)
        layout.addWidget(panel)
        return page

    def _set_controls_enabled(self, enabled: bool) -> None:
        self.save_button.setEnabled(enabled)
        self.save_as_button.setEnabled(enabled)
        self.system_button.setEnabled(enabled)

    def _set_dirty(self, dirty: bool) -> None:
        self._dirty = dirty
        self.dirty_label.setVisible(dirty)

    def can_close(self) -> bool:
        if not self._dirty:
            return True
        answer = QMessageBox.question(
            self,
            "Kaydedilmemiş değişiklikler",
            "Çıktı düzenleyicide kaydedilmemiş değişiklikler var. Devam edilsin mi?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        return answer == QMessageBox.StandardButton.Yes

    def _open_dialog(self) -> None:
        if not self.can_close():
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Belge aç", "", "Word/Excel (*.docx *.xlsx)"
        )
        if path:
            self.open_path(path)

    def open_path(self, path: str | Path) -> None:
        path = Path(path)
        suffix = path.suffix.lower()
        try:
            if suffix == ".docx":
                self._load_word(path)
            elif suffix == ".xlsx":
                self._load_excel(path)
            else:
                QMessageBox.warning(self, "Desteklenmeyen dosya", "Yalnızca .docx ve .xlsx desteklenir.")
                return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Belge açılamadı", str(exc))
            return
        self.file_label.setText(path.name)
        self._set_dirty(False)
        self._set_controls_enabled(True)
        self.status.setText(f"Açıldı: {path.name}")

    def _load_word(self, path: Path) -> None:
        self.word_editor = WordDocumentEditor(path)
        self.excel_editor = None
        self._loading = True
        self.table_label.setVisible(True)
        self.table_combo.setVisible(True)
        self.sheet_label.setVisible(False)
        self.sheet_combo.setVisible(False)

        self.paragraph_list.clear()
        for i, text in enumerate(self.word_editor.paragraph_texts()):
            preview = text if len(text) <= 90 else text[:87] + "…"
            item = QListWidgetItem(f"{i + 1:>4}   {preview}")
            item.setData(Qt.ItemDataRole.UserRole, i)
            self.paragraph_list.addItem(item)

        self.table_combo.clear()
        if self.word_editor.table_count:
            for i in range(self.word_editor.table_count):
                self.table_combo.addItem(self.word_editor.table_label(i), i)
            self.table_combo.setEnabled(True)
            self._table_changed(0)
        else:
            self.table_combo.addItem("Tablo yok", -1)
            self.table_combo.setEnabled(False)
            self.word_table_grid.clear()
            self.word_table_grid.setRowCount(0)
            self.word_table_grid.setColumnCount(0)
        self._loading = False
        self.stack.setCurrentIndex(1)

    def _load_excel(self, path: Path) -> None:
        self.excel_editor = ExcelWorkbookEditor(path)
        self.word_editor = None
        self.table_label.setVisible(False)
        self.table_combo.setVisible(False)
        self.sheet_label.setVisible(True)
        self.sheet_combo.setVisible(True)

        self.sheet_combo.clear()
        for name in self.excel_editor.sheet_names:
            self.sheet_combo.addItem(name)
        self._sheet_changed(0)
        self.stack.setCurrentIndex(2)

    def _table_changed(self, index: int) -> None:
        if self.word_editor is None or index < 0:
            return
        table_index = self.table_combo.itemData(index)
        if table_index is None or table_index < 0:
            return
        self._loading = True
        data = self.word_editor.table_data(table_index)
        rows = min(len(data), UI_MAX_ROWS)
        cols = min(max((len(r) for r in data), default=0), UI_MAX_COLS)
        self.word_table_grid.clear()
        self.word_table_grid.setRowCount(rows)
        self.word_table_grid.setColumnCount(cols)
        self.word_table_grid.setHorizontalHeaderLabels(
            [f"Sütun {c + 1}" for c in range(cols)]
        )
        self.word_table_grid.setVerticalHeaderLabels([str(r + 1) for r in range(rows)])
        for r in range(rows):
            for c in range(cols):
                text = data[r][c] if c < len(data[r]) else ""
                self.word_table_grid.setItem(r, c, QTableWidgetItem(text))
        self._loading = False

    def _sheet_changed(self, index: int) -> None:
        if self.excel_editor is None or index < 0:
            return
        sheet = self.sheet_combo.currentText()
        used_rows, used_cols = self.excel_editor.used_shape(sheet)
        rows = min(used_rows, UI_MAX_ROWS)
        cols = min(used_cols, UI_MAX_COLS)
        self._loading = True
        self.excel_grid.clear()
        self.excel_grid.setRowCount(rows)
        self.excel_grid.setColumnCount(cols)
        self.excel_grid.setHorizontalHeaderLabels(
            [get_column_letter(c + 1) for c in range(cols)]
        )
        self.excel_grid.setVerticalHeaderLabels([str(r + 1) for r in range(rows)])
        for r in range(1, rows + 1):
            for c in range(1, cols + 1):
                self.excel_grid.setItem(
                    r - 1, c - 1, QTableWidgetItem(self.excel_editor.cell_text(sheet, r, c))
                )
        self._loading = False
        if rows < used_rows or cols < used_cols:
            self.status.setText(
                f"Görüntülenen alan {rows}×{cols} ile sınırlı; belgenin tamamı korunur"
            )
        else:
            self.status.setText(f"Sayfa: {sheet}")

    def _edit_paragraph(self, item: QListWidgetItem) -> None:
        if self.word_editor is None:
            return
        index = item.data(Qt.ItemDataRole.UserRole)
        current = self.word_editor.paragraph_texts()[index]
        text, ok = QInputDialog.getMultiLineText(self, "Paragrafı düzenle", "Metin:", current)
        if not ok or text == current:
            return
        self.word_editor.set_paragraph_text(index, text)
        preview = text if len(text) <= 90 else text[:87] + "…"
        item.setText(f"{index + 1:>4}   {preview}")
        self._set_dirty(True)

    def _word_cell_changed(self, item: QTableWidgetItem) -> None:
        if self._loading or self.word_editor is None:
            return
        table_index = self.table_combo.currentData()
        if table_index is None or table_index < 0:
            return
        self.word_editor.set_table_cell(table_index, item.row(), item.column(), item.text())
        self._set_dirty(True)

    def _excel_cell_changed(self, item: QTableWidgetItem) -> None:
        if self._loading or self.excel_editor is None:
            return
        sheet = self.sheet_combo.currentText()
        self.excel_editor.set_cell_text(sheet, item.row() + 1, item.column() + 1, item.text())
        self._set_dirty(True)

    def _save(self) -> None:
        editor = self.word_editor or self.excel_editor
        if editor is None:
            return
        try:
            path = editor.save()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Kaydedilemedi", str(exc))
            return
        self._set_dirty(False)
        self.status.setText(f"Kaydedildi: {path.name}")

    def _save_as(self) -> None:
        editor = self.word_editor or self.excel_editor
        if editor is None:
            return
        suffix = ".docx" if self.word_editor is not None else ".xlsx"
        path, _ = QFileDialog.getSaveFileName(
            self, "Farklı kaydet", editor.path.name, f"Belge (*{suffix})"
        )
        if not path:
            return
        try:
            saved = editor.save(path)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Kaydedilemedi", str(exc))
            return
        self.file_label.setText(saved.name)
        self._set_dirty(False)
        self.status.setText(f"Kaydedildi: {saved.name}")

    def _open_in_system(self) -> None:
        editor = self.word_editor or self.excel_editor
        if editor is None:
            return
        if self._dirty:
            self._save()
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(editor.path)))
