from __future__ import annotations

from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.core.pipeline import available_ocr_engines
from app.ui.convert_tab import ConvertTab
from app.ui.output_editor_tab import OutputEditorTab
from app.ui.pdf_editor_tab import PdfEditorTab
from app.ui.settings_store import SettingsStore


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Pdf2 — Belge Atölyesi")
        self.resize(1060, 720)
        self.setMinimumSize(880, 600)

        self._settings = SettingsStore()
        canvas = QWidget()
        canvas.setObjectName("Canvas")
        layout = QVBoxLayout(canvas)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._build_header())

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.convert_tab = ConvertTab(settings=self._settings)
        self.tabs.addTab(self.convert_tab, "Dönüştür")
        self.pdf_editor_tab = PdfEditorTab()
        self.tabs.addTab(self.pdf_editor_tab, "PDF Düzenle")
        self.output_editor_tab = OutputEditorTab()
        self.tabs.addTab(self.output_editor_tab, "Çıktı Düzenle")
        layout.addWidget(self.tabs, 1)

        self.setCentralWidget(canvas)
        self.setStatusBar(QStatusBar())

        geometry = self._settings.get_bytes("window/geometry")
        if not geometry.isEmpty():
            self.restoreGeometry(geometry)

        QShortcut(QKeySequence.StandardKey.Open, self, activated=self.pdf_editor_tab._open_dialog)
        QShortcut(QKeySequence.StandardKey.Save, self, activated=self.pdf_editor_tab.save_current)

        engines = available_ocr_engines()
        if engines:
            self.statusBar().showMessage("OCR hazır: " + ", ".join(engines))
        else:
            self.statusBar().showMessage(
                "OCR motoru bulunamadı — Tesseract kurun veya RapidOCR paketini yükleyin"
            )

    def _build_header(self) -> QFrame:
        header = QFrame()
        header.setObjectName("Header")
        header.setFixedHeight(64)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(10)

        wordmark = QLabel("PDF2")
        wordmark.setObjectName("Wordmark")
        layout.addWidget(wordmark)

        subtitle = QLabel("Belge Atölyesi")
        subtitle.setObjectName("Subtitle")
        layout.addWidget(subtitle)
        layout.addStretch(1)

        engines = available_ocr_engines()
        engine_label = QLabel(
            "OCR: " + (", ".join(engines) if engines else "yok")
        )
        engine_label.setObjectName("Mono")
        engine_label.setToolTip("Algılanan OCR motorları")
        layout.addWidget(engine_label)
        return header

    def closeEvent(self, event) -> None:  # noqa: ANN001
        if self.convert_tab.is_busy():
            answer = QMessageBox.question(
                self,
                "Dönüşüm sürüyor",
                "Dönüşüm devam ediyor. Yine de çıkılsın mı?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            if not self.convert_tab.shutdown():
                QMessageBox.information(
                    self,
                    "Dönüşüm sürüyor",
                    "Geçerli dosyanın dönüşümü tamamlanana kadar bekleyin, sonra tekrar kapatın.",
                )
                event.ignore()
                return
        if not self.pdf_editor_tab.can_close() or not self.output_editor_tab.can_close():
            event.ignore()
            return
        self._settings.set_bytes("window/geometry", self.saveGeometry())
        self.convert_tab.save_settings()
        self.pdf_editor_tab.close_session()
        super().closeEvent(event)
