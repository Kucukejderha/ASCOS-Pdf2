from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.core.models import ConversionOptions, ConvertMode, ExcelLayout
from app.core.pipeline import available_ocr_engines
from app.ui.settings_store import SettingsStore
from app.workers import ConversionWorker, start_worker


class FileDropList(QListWidget):
    files_dropped = Signal(list)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.setAlternatingRowColors(False)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            paths = [u.toLocalFile() for u in event.mimeData().urls()]
            if any(p.lower().endswith(".pdf") for p in paths):
                event.acceptProposedAction()

    def dragMoveEvent(self, event) -> None:  # noqa: ANN001
        event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        paths = [u.toLocalFile() for u in event.mimeData().urls()]
        pdfs = [p for p in paths if p.lower().endswith(".pdf")]
        if pdfs:
            self.files_dropped.emit(pdfs)
            event.acceptProposedAction()


class JobRow(QFrame):
    def __init__(self, index: int, path: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.index = index
        self.output_path: Path | None = None

        self.setObjectName("Panel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        top = QHBoxLayout()
        top.setSpacing(8)
        name = QLabel(path.name)
        name.setObjectName("SectionTitle")
        top.addWidget(name, 1)
        self.status = QLabel("Sırada")
        self.status.setObjectName("Muted")
        top.addWidget(self.status)
        self.open_button = QPushButton("Klasörde göster")
        self.open_button.setObjectName("Ghost")
        self.open_button.setVisible(False)
        self.open_button.clicked.connect(self._open_folder)
        top.addWidget(self.open_button)
        layout.addLayout(top)

        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.bar.setTextVisible(False)
        layout.addWidget(self.bar)

    def set_progress(self, fraction: float, message: str) -> None:
        self.bar.setValue(int(fraction * 100))
        self.status.setText(message)

    def set_done(self, output: Path, elapsed: str) -> None:
        self.output_path = output
        self.bar.setValue(100)
        self.bar.setProperty("done", True)
        self.bar.style().unpolish(self.bar)
        self.bar.style().polish(self.bar)
        self.status.setText(f"Bitti — {elapsed}")
        self.open_button.setVisible(True)

    def set_error(self, message: str) -> None:
        self.bar.setProperty("error", True)
        self.bar.style().unpolish(self.bar)
        self.bar.style().polish(self.bar)
        self.status.setText(f"Hata: {message}")

    def _open_folder(self) -> None:
        if not self.output_path:
            return
        folder = str(self.output_path.parent)
        if sys.platform == "win32":
            subprocess.Popen(["explorer", "/select,", str(self.output_path)])
        else:
            os.startfile(folder)  # type: ignore[attr-defined]


class ConvertTab(QWidget):
    def __init__(self, parent: QWidget | None = None, settings: SettingsStore | None = None) -> None:
        super().__init__(parent)
        self._thread = None
        self._worker: ConversionWorker | None = None
        self._job_rows: list[JobRow] = []
        self._settings = settings or SettingsStore()
        self._build_ui()
        self._refresh_engine_combo()
        self._load_settings()

    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(14)

        root.addWidget(self._build_files_panel(), 0)
        root.addWidget(self._build_work_panel(), 1)

    def _build_files_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("Panel")
        panel.setMinimumWidth(250)
        panel.setMaximumWidth(330)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        title = QLabel("Dosyalar")
        title.setObjectName("PanelTitle")
        layout.addWidget(title)

        self.file_list = FileDropList()
        self.file_list.files_dropped.connect(self.add_files)
        self.file_list.setToolTip("PDF dosyalarını buraya sürükleyin")
        layout.addWidget(self.file_list, 1)

        self.file_count = QLabel("Henüz dosya eklenmedi")
        self.file_count.setObjectName("Muted")
        layout.addWidget(self.file_count)

        buttons = QHBoxLayout()
        add = QPushButton("PDF ekle")
        add.clicked.connect(self._browse_files)
        buttons.addWidget(add)
        remove = QPushButton("Kaldır")
        remove.clicked.connect(self._remove_selected)
        buttons.addWidget(remove)
        layout.addLayout(buttons)

        clear = QPushButton("Listeyi temizle")
        clear.setObjectName("Ghost")
        clear.clicked.connect(self._clear_files)
        layout.addWidget(clear)
        return panel

    def _build_work_panel(self) -> QWidget:
        wrap = QWidget()
        layout = QVBoxLayout(wrap)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        settings = QFrame()
        settings.setObjectName("Panel")
        s = QVBoxLayout(settings)
        s.setContentsMargins(14, 12, 14, 14)
        s.setSpacing(10)

        title = QLabel("Dönüşüm ayarları")
        title.setObjectName("PanelTitle")
        s.addWidget(title)

        mode_row = QHBoxLayout()
        mode_row.setSpacing(18)
        mode_row.addWidget(QLabel("Hedef"))
        self.radio_word = QRadioButton("Word (.docx)")
        self.radio_word.setChecked(True)
        self.radio_excel = QRadioButton("Excel (.xlsx)")
        self.radio_word.toggled.connect(self._mode_changed)
        mode_row.addWidget(self.radio_word)
        mode_row.addWidget(self.radio_excel)
        mode_row.addStretch(1)
        mode_row.addWidget(QLabel("Sayfalar"))
        self.pages_edit = QLineEdit()
        self.pages_edit.setPlaceholderText("Tümü — örn: 1-3,5")
        self.pages_edit.setMaximumWidth(160)
        mode_row.addWidget(self.pages_edit)
        s.addLayout(mode_row)

        ocr_row = QHBoxLayout()
        ocr_row.setSpacing(12)
        self.ocr_check = QCheckBox("Taranmış sayfaları OCR ile oku")
        self.ocr_check.setChecked(True)
        ocr_row.addWidget(self.ocr_check)
        self.force_ocr_check = QCheckBox("Tüm sayfaları OCR et")
        ocr_row.addWidget(self.force_ocr_check)
        ocr_row.addStretch(1)
        s.addLayout(ocr_row)

        engine_row = QHBoxLayout()
        engine_row.setSpacing(12)
        engine_row.addWidget(QLabel("OCR motoru"))
        self.engine_combo = QComboBox()
        self.engine_combo.setMinimumWidth(170)
        engine_row.addWidget(self.engine_combo)
        engine_row.addSpacing(8)
        engine_row.addWidget(QLabel("Dil"))
        self.lang_edit = QLineEdit("tur+eng")
        self.lang_edit.setMaximumWidth(110)
        engine_row.addWidget(self.lang_edit)
        engine_row.addStretch(1)
        self.excel_layout_label = QLabel("Excel düzeni")
        engine_row.addWidget(self.excel_layout_label)
        self.excel_layout_combo = QComboBox()
        self.excel_layout_combo.addItem("Sayfa başına sekme", ExcelLayout.PAGE_PER_SHEET)
        self.excel_layout_combo.addItem("Tümü tek sekmede", ExcelLayout.ALL_IN_ONE)
        engine_row.addWidget(self.excel_layout_combo)
        s.addLayout(engine_row)

        out_row = QHBoxLayout()
        out_row.setSpacing(8)
        out_row.addWidget(QLabel("Çıktı klasörü"))
        self.output_edit = QLineEdit()
        self.output_edit.setPlaceholderText("Kaynak dosyanın klasörü")
        out_row.addWidget(self.output_edit, 1)
        browse = QPushButton("Gözat…")
        browse.clicked.connect(self._browse_output)
        out_row.addWidget(browse)
        s.addLayout(out_row)
        layout.addWidget(settings)

        jobs_panel = QFrame()
        jobs_panel.setObjectName("Panel")
        j = QVBoxLayout(jobs_panel)
        j.setContentsMargins(14, 12, 14, 12)
        j.setSpacing(8)
        self.jobs_title = QLabel("İşlem durumu")
        self.jobs_title.setObjectName("PanelTitle")
        j.addWidget(self.jobs_title)

        self.jobs_area = QScrollArea()
        self.jobs_area.setWidgetResizable(True)
        self.jobs_container = QWidget()
        self.jobs_layout = QVBoxLayout(self.jobs_container)
        self.jobs_layout.setContentsMargins(0, 0, 0, 0)
        self.jobs_layout.setSpacing(8)
        self.jobs_empty = QLabel(
            "Dönüşüm başladığında her dosyanın ilerlemesi burada görünür"
        )
        self.jobs_empty.setObjectName("Muted")
        self.jobs_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.jobs_layout.addWidget(self.jobs_empty)
        self.jobs_layout.addStretch(1)
        self.jobs_area.setWidget(self.jobs_container)
        j.addWidget(self.jobs_area, 1)
        layout.addWidget(jobs_panel, 1)

        actions = QHBoxLayout()
        self.summary_label = QLabel("Dosya ekleyin veya sürükleyip bırakın")
        self.summary_label.setObjectName("Muted")
        actions.addWidget(self.summary_label)
        actions.addStretch(1)
        self.cancel_button = QPushButton("İptal")
        self.cancel_button.setObjectName("Danger")
        self.cancel_button.setVisible(False)
        self.cancel_button.clicked.connect(self._cancel)
        actions.addWidget(self.cancel_button)
        self.convert_button = QPushButton("Dönüştür")
        self.convert_button.setObjectName("Primary")
        self.convert_button.clicked.connect(self._start_conversion)
        actions.addWidget(self.convert_button)
        layout.addLayout(actions)

        self._mode_changed()
        return wrap

    def _refresh_engine_combo(self) -> None:
        self.engine_combo.clear()
        self.engine_combo.addItem("Otomatik", "auto")
        engines = available_ocr_engines()
        tooltip = "Algılanan: " + (", ".join(engines) if engines else "yok")
        self.engine_combo.addItem("Tesseract", "tesseract")
        self.engine_combo.addItem("RapidOCR", "rapidocr")
        self.engine_combo.setToolTip(tooltip)

    def _load_settings(self) -> None:
        s = self._settings
        if s.get_str("convert/mode") == "excel":
            self.radio_excel.setChecked(True)
        self.pages_edit.setText(s.get_str("convert/pages"))
        self.ocr_check.setChecked(s.get_bool("convert/ocr", True))
        self.force_ocr_check.setChecked(s.get_bool("convert/force_ocr", False))
        engine = s.get_str("convert/engine", "auto")
        index = self.engine_combo.findData(engine)
        if index >= 0:
            self.engine_combo.setCurrentIndex(index)
        self.lang_edit.setText(s.get_str("convert/lang", "tur+eng"))
        layout = s.get_str("convert/layout", ExcelLayout.PAGE_PER_SHEET.value)
        layout_index = self.excel_layout_combo.findData(ExcelLayout(layout))
        if layout_index >= 0:
            self.excel_layout_combo.setCurrentIndex(layout_index)
        self.output_edit.setText(s.get_str("convert/output_dir"))
        self._mode_changed()

    def save_settings(self) -> None:
        s = self._settings
        s.set_str("convert/mode", "excel" if self.radio_excel.isChecked() else "word")
        s.set_str("convert/pages", self.pages_edit.text().strip())
        s.set_bool("convert/ocr", self.ocr_check.isChecked())
        s.set_bool("convert/force_ocr", self.force_ocr_check.isChecked())
        s.set_str("convert/engine", self.engine_combo.currentData() or "auto")
        s.set_str("convert/lang", self.lang_edit.text().strip())
        s.set_str("convert/layout", str(self.excel_layout_combo.currentData() or ExcelLayout.PAGE_PER_SHEET.value))
        s.set_str("convert/output_dir", self.output_edit.text().strip())
        s.sync()

    def _mode_changed(self) -> None:
        is_excel = self.radio_excel.isChecked()
        self.excel_layout_combo.setVisible(is_excel)
        self.excel_layout_label.setVisible(is_excel)

    def _browse_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(self, "PDF seç", "", "PDF dosyaları (*.pdf)")
        if paths:
            self.add_files(paths)

    def add_files(self, paths: list[str]) -> None:
        existing = {
            self.file_list.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(self.file_list.count())
        }
        for path in paths:
            if path in existing:
                continue
            item = QListWidgetItem(Path(path).name)
            item.setData(Qt.ItemDataRole.UserRole, path)
            item.setToolTip(path)
            self.file_list.addItem(item)
            existing.add(path)
        self._update_count()

    def _remove_selected(self) -> None:
        for item in self.file_list.selectedItems():
            self.file_list.takeItem(self.file_list.row(item))
        self._update_count()

    def _clear_files(self) -> None:
        self.file_list.clear()
        self._update_count()

    def _update_count(self) -> None:
        n = self.file_list.count()
        self.file_count.setText(f"{n} dosya" if n else "Henüz dosya eklenmedi")
        self.summary_label.setText(
            f"{n} dosya dönüştürmeye hazır" if n else "Dosya ekleyin veya sürükleyip bırakın"
        )

    def _browse_output(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Çıktı klasörü seç")
        if folder:
            self.output_edit.setText(folder)

    def _files(self) -> list[Path]:
        return [
            Path(self.file_list.item(i).data(Qt.ItemDataRole.UserRole))
            for i in range(self.file_list.count())
        ]

    def _clear_jobs(self) -> None:
        for row in self._job_rows:
            self.jobs_layout.removeWidget(row)
            row.deleteLater()
        self._job_rows.clear()
        self.jobs_empty.setVisible(True)

    def _start_conversion(self) -> None:
        files = self._files()
        if not files:
            self.summary_label.setText("Önce PDF ekleyin")
            return
        if self._thread is not None:
            if self._thread.isRunning():
                return
            self._thread = None
            self._worker = None

        self.save_settings()
        options = ConversionOptions(
            mode=ConvertMode.EXCEL if self.radio_excel.isChecked() else ConvertMode.WORD,
            pages=self.pages_edit.text().strip(),
            ocr=self.ocr_check.isChecked(),
            force_ocr=self.force_ocr_check.isChecked(),
            ocr_engine=self.engine_combo.currentData(),
            ocr_lang=self.lang_edit.text().strip() or "tur+eng",
            excel_layout=ExcelLayout(self.excel_layout_combo.currentData()),
        )
        output_dir = Path(self.output_edit.text()) if self.output_edit.text().strip() else None
        if output_dir:
            output_dir.mkdir(parents=True, exist_ok=True)

        self._clear_jobs()
        self.jobs_empty.setVisible(False)
        for i, src in enumerate(files):
            row = JobRow(i, src)
            self._job_rows.append(row)
            self.jobs_layout.insertWidget(self.jobs_layout.count() - 1, row)

        self._worker = ConversionWorker(files, options, output_dir)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)
        self._worker.all_done.connect(self._on_all_done)
        self._thread = start_worker(self._worker, parent=self)
        self._thread.finished.connect(self._on_thread_finished)
        self._thread.start()

        self.convert_button.setEnabled(False)
        self.cancel_button.setVisible(True)
        self.summary_label.setText(f"0/{len(files)} tamamlandı")

    def _cancel(self) -> None:
        if self._worker:
            self._worker.cancel()
            self.cancel_button.setEnabled(False)
            self.summary_label.setText("İptal ediliyor…")

    def _on_progress(self, index: int, fraction: float, message: str) -> None:
        if 0 <= index < len(self._job_rows):
            self._job_rows[index].set_progress(fraction, message)

    def _on_finished(self, index: int, result) -> None:  # noqa: ANN001
        from app.core.utils import format_elapsed

        row = self._job_rows[index]
        row.set_done(result.output, format_elapsed(result.elapsed_s))
        done = sum(1 for r in self._job_rows if r.output_path)
        self.summary_label.setText(f"{done}/{len(self._job_rows)} tamamlandı")

    def _on_failed(self, index: int, message: str) -> None:
        if 0 <= index < len(self._job_rows):
            self._job_rows[index].set_error(message)

    def _on_all_done(self) -> None:
        self.convert_button.setEnabled(True)
        self.cancel_button.setVisible(False)
        self.cancel_button.setEnabled(True)

    def _on_thread_finished(self) -> None:
        self._thread = None
        self._worker = None

    def is_busy(self) -> bool:
        return self._thread is not None and self._thread.isRunning()

    def shutdown(self) -> bool:
        """Süren dönüşümü iptal edip thread'in kapanmasını bekler."""
        if self._worker is not None:
            self._worker.cancel()
        if self._thread is not None:
            self._thread.quit()
            return self._thread.wait(10000)
        return True
