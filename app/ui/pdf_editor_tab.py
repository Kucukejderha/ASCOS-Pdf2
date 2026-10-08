from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QBuffer, QIODevice, QPoint, QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QColorDialog,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QRubberBand,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.core.pdf_editor.page_ops import PdfEditSession, PdfPasswordError, split_pdf
from app.core.pdf_editor.text_tools import extract_rect_text
from app.ui.pdf_thumbs import ThumbnailList
from app.ui.security_dialogs import FormFillDialog, PasswordDialog
from app.ui.stamp_dialogs import PageNumberDialog, WatermarkDialog


class PageView(QLabel):
    highlight_rect = Signal(QRect)
    text_click = Signal(QPoint)
    note_click = Signal(QPoint)
    selection_made = Signal(QRect)
    selection_cleared = Signal()
    copy_requested = Signal()
    erase_rect = Signal(QRect)
    redact_rect = Signal(QRect)
    edit_rect = Signal(QRect)
    crop_rect = Signal(QRect)
    pen_drawn = Signal(list)
    shape_rect_drawn = Signal(str, QRect)
    shape_line_drawn = Signal(str, QPoint, QPoint)
    image_rect_drawn = Signal(str, QRect)

    _RECT_TOOLS = (
        "highlight",
        "select",
        "erase",
        "redact",
        "edit",
        "shape_rect",
        "shape_ellipse",
        "shape_line",
        "shape_arrow",
        "image",
        "signature",
        "crop",
    )

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.tool = "select"
        self._origin: QPoint | None = None
        self._band: QRubberBand | None = None
        self._pen_points: list[QPoint] = []
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCursor(Qt.CursorShape.ArrowCursor)

    def set_tool(self, tool: str) -> None:
        if tool != "select" and self._band is not None and self._band.isVisible():
            self._band.hide()
            self.selection_cleared.emit()
        self.tool = tool
        cursors = {
            "highlight": Qt.CursorShape.IBeamCursor,
            "text": Qt.CursorShape.IBeamCursor,
            "note": Qt.CursorShape.PointingHandCursor,
            "select": Qt.CursorShape.IBeamCursor,
            "erase": Qt.CursorShape.CrossCursor,
            "redact": Qt.CursorShape.CrossCursor,
            "edit": Qt.CursorShape.IBeamCursor,
            "pen": Qt.CursorShape.CrossCursor,
            "shape_rect": Qt.CursorShape.CrossCursor,
            "shape_ellipse": Qt.CursorShape.CrossCursor,
            "shape_line": Qt.CursorShape.CrossCursor,
            "shape_arrow": Qt.CursorShape.CrossCursor,
            "image": Qt.CursorShape.CrossCursor,
            "signature": Qt.CursorShape.CrossCursor,
            "crop": Qt.CursorShape.CrossCursor,
        }
        self.setCursor(cursors.get(tool, Qt.CursorShape.ArrowCursor))

    def contextMenuEvent(self, event) -> None:  # noqa: ANN001
        menu = QMenu(self)
        copy_action = menu.addAction("Kopyala")
        copy_action.triggered.connect(self.copy_requested.emit)
        menu.exec(event.globalPos())

    def mousePressEvent(self, event) -> None:  # noqa: ANN001
        if self.pixmap() is None or event.button() != Qt.MouseButton.LeftButton:
            return
        if self.tool == "pen":
            self._pen_points = [event.position().toPoint()]
            return
        if self.tool in self._RECT_TOOLS:
            if self.tool == "select" and self._band is not None:
                self._band.hide()
                self.selection_cleared.emit()
            self._origin = event.position().toPoint()
            if self._band is None:
                self._band = QRubberBand(QRubberBand.Shape.Rectangle, self)
            self._band.setGeometry(QRect(self._origin, QSize()))
            self._band.show()
        elif self.tool == "text":
            self.text_click.emit(event.position().toPoint())
        elif self.tool == "note":
            self.note_click.emit(event.position().toPoint())

    def mouseMoveEvent(self, event) -> None:  # noqa: ANN001
        if self.tool == "pen" and self._pen_points:
            self._pen_points.append(event.position().toPoint())
            return
        if self._origin is not None and self._band is not None:
            rect = QRect(self._origin, event.position().toPoint()).normalized()
            self._band.setGeometry(rect)

    def mouseReleaseEvent(self, event) -> None:  # noqa: ANN001
        if self.tool == "pen":
            points = self._pen_points
            self._pen_points = []
            if len(points) > 1:
                self.pen_drawn.emit(points)
            return
        if self._origin is None or self._band is None:
            return
        end_point = event.position().toPoint()
        rect = QRect(self._origin, end_point).normalized()
        origin = self._origin
        self._origin = None
        is_drag = rect.width() > 4 and rect.height() > 4
        if self.tool == "select":
            if is_drag:
                self._band.setGeometry(rect)
                self.selection_made.emit(rect)
            else:
                self._band.hide()
                self.selection_cleared.emit()
            return
        self._band.hide()
        if self.tool == "shape_rect":
            if is_drag:
                self.shape_rect_drawn.emit("rect", rect)
            return
        if self.tool == "shape_ellipse":
            if is_drag:
                self.shape_rect_drawn.emit("ellipse", rect)
            return
        if self.tool == "shape_line":
            self.shape_line_drawn.emit("line", origin, end_point)
            return
        if self.tool == "shape_arrow":
            self.shape_line_drawn.emit("arrow", origin, end_point)
            return
        if self.tool in ("image", "signature"):
            if is_drag:
                self.image_rect_drawn.emit(self.tool, rect)
            return
        if self.tool == "crop":
            if is_drag:
                self.crop_rect.emit(rect)
            return
        if not is_drag:
            return
        if self.tool == "erase":
            self.erase_rect.emit(rect)
        elif self.tool == "redact":
            self.redact_rect.emit(rect)
        elif self.tool == "edit":
            self.edit_rect.emit(rect)
        else:
            self.highlight_rect.emit(rect)

    def clear_selection(self) -> None:
        if self._band is not None and self._band.isVisible():
            self._band.hide()
        self.selection_cleared.emit()


class PdfEditorTab(QWidget):
    MIN_ZOOM = 0.5
    MAX_ZOOM = 4.0

    TOOLS: tuple[tuple[str, str, str], ...] = (
        ("select", "Seç", "Metin seçme ve gezinme"),
        ("highlight", "Vurgula", "Metin üzerine sürükleyerek vurgu ekleyin"),
        ("edit", "Metni düzelt", "Seçili metni silip yerine yenisini yazın"),
        ("text", "Metin", "Sayfaya tıklayıp metin ekleyin"),
        ("note", "Not", "Sayfaya tıklayıp yapışkan not ekleyin"),
        ("erase", "Beyazlat", "Alanı beyaz dikdörtgenle kapatır (görsel)"),
        ("redact", "Sil (gerçek)", "Alanın altındaki metni kalıcı olarak siler"),
        ("pen", "Kalem", "Serbest çizim yapın"),
        ("shape_rect", "Dikdörtgen", "Sürükleyerek dikdörtgen çizin"),
        ("shape_ellipse", "Elips", "Sürükleyerek elips çizin"),
        ("shape_line", "Çizgi", "Başlangıç ve bitiş noktası seçin"),
        ("shape_arrow", "Ok", "Başlangıç ve bitiş noktası seçin"),
        ("image", "Görsel", "Sürükleyin; panodaki görsel veya dosya yerleştirilir"),
        ("signature", "İmza", "İmza görseli yerleştirin (pano veya dosya)"),
        ("crop", "Kırp", "Sürükleyip kırpma alanını seçin"),
    )

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.session: PdfEditSession | None = None
        self.page_index = 0
        self.zoom = 1.25
        self._selection_text = ""
        self._page_clipboard: list[bytes] = []
        self.draw_color = QColor("#22252A")
        self.draw_width = 2.0
        self._tool_buttons: dict[str, QPushButton] = {}
        self._build_ui()
        QShortcut(QKeySequence.StandardKey.Undo, self, activated=self.undo)
        QShortcut(QKeySequence.StandardKey.Redo, self, activated=self.redo)
        QShortcut(QKeySequence("Ctrl+Shift+Z"), self, activated=self.redo)
        QShortcut(QKeySequence.StandardKey.Copy, self, activated=self.copy_selection)
        self._set_enabled(False)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(10)

        toolbar = QFrame()
        toolbar.setObjectName("Panel")
        bar = QHBoxLayout(toolbar)
        bar.setContentsMargins(12, 8, 12, 8)
        bar.setSpacing(6)

        self.open_button = QPushButton("PDF aç…")
        self.open_button.clicked.connect(self._open_dialog)
        bar.addWidget(self.open_button)

        self.file_label = QLabel("Dosya açılmadı")
        self.file_label.setObjectName("Muted")
        bar.addWidget(self.file_label)
        bar.addSpacing(8)
        bar.addWidget(self._separator())

        self.undo_button = QPushButton("Geri al")
        self.undo_button.setToolTip("Son işlemi geri al (Ctrl+Z)")
        self.undo_button.clicked.connect(self.undo)
        bar.addWidget(self.undo_button)
        self.redo_button = QPushButton("İleri al")
        self.redo_button.setToolTip("Geri alınan işlemi yinele (Ctrl+Y)")
        self.redo_button.clicked.connect(self.redo)
        bar.addWidget(self.redo_button)
        bar.addSpacing(8)
        bar.addWidget(self._separator())

        self.page_menu_button = QPushButton("Sayfa işlemleri ▾")
        self.page_menu_button.setToolTip("Döndür, sil, taşı, PDF ekle, böl")
        self.page_menu_button.clicked.connect(self._show_page_menu)
        self._build_page_menu()
        bar.addWidget(self.page_menu_button)

        bar.addSpacing(8)
        bar.addWidget(self._separator())
        self.color_button = QPushButton("")
        self.color_button.setFixedSize(28, 22)
        self.color_button.setToolTip("Çizim rengi seç")
        self.color_button.clicked.connect(self._pick_draw_color)
        bar.addWidget(self.color_button)
        bar.addWidget(QLabel("Kalınlık"))
        self.width_spin = QSpinBox()
        self.width_spin.setRange(1, 12)
        self.width_spin.setValue(int(self.draw_width))
        self.width_spin.valueChanged.connect(self._width_changed)
        bar.addWidget(self.width_spin)
        self._apply_color_swatch()

        bar.addSpacing(8)
        self.thumbs_toggle = QPushButton("Küçük resim")
        self.thumbs_toggle.setCheckable(True)
        self.thumbs_toggle.setChecked(True)
        self.thumbs_toggle.setToolTip("Sayfa küçük resim panelini göster/gizle")
        self.thumbs_toggle.toggled.connect(self._toggle_thumbnails)
        bar.addWidget(self.thumbs_toggle)

        bar.addStretch(1)
        self.save_as_button = QPushButton("Farklı kaydet…")
        self.save_as_button.setObjectName("Ghost")
        self.save_as_button.clicked.connect(self.save_as)
        bar.addWidget(self.save_as_button)
        self.save_button = QPushButton("Kaydet")
        self.save_button.setObjectName("Primary")
        self.save_button.clicked.connect(self._save)
        bar.addWidget(self.save_button)
        root.addWidget(toolbar)

        view_panel = QFrame()
        view_panel.setObjectName("Panel")
        view_layout = QHBoxLayout(view_panel)
        view_layout.setContentsMargins(0, 0, 0, 0)
        view_layout.setSpacing(0)

        self.thumb_panel = QFrame()
        self.thumb_panel.setObjectName("Panel")
        self.thumb_panel.setFixedWidth(150)
        thumb_layout = QVBoxLayout(self.thumb_panel)
        thumb_layout.setContentsMargins(8, 8, 8, 8)
        thumb_layout.setSpacing(6)
        thumb_title = QLabel("Sayfalar")
        thumb_title.setObjectName("PanelTitle")
        thumb_layout.addWidget(thumb_title)
        self.thumbnails = ThumbnailList()
        self.thumbnails.order_changed.connect(self._on_thumbnails_reordered)
        self.thumbnails.page_activated.connect(self._go_to)
        self.thumbnails.context_menu_requested.connect(self._show_thumb_menu)
        thumb_layout.addWidget(self.thumbnails, 1)
        view_layout.addWidget(self.thumb_panel)

        view_layout.addWidget(self._build_tool_strip())

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(False)
        self.scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_view = PageView()
        self.page_view.highlight_rect.connect(self._on_highlight)
        self.page_view.text_click.connect(self._on_text_click)
        self.page_view.note_click.connect(self._on_note_click)
        self.page_view.selection_made.connect(self._on_selection)
        self.page_view.selection_cleared.connect(self._clear_selection)
        self.page_view.copy_requested.connect(self.copy_selection)
        self.page_view.erase_rect.connect(self._on_erase)
        self.page_view.redact_rect.connect(self._on_redact)
        self.page_view.edit_rect.connect(self._on_edit)
        self.page_view.pen_drawn.connect(self._on_pen)
        self.page_view.shape_rect_drawn.connect(self._on_shape_rect)
        self.page_view.shape_line_drawn.connect(self._on_shape_line)
        self.page_view.image_rect_drawn.connect(self._on_image_rect)
        self.page_view.crop_rect.connect(self._on_crop)
        self.scroll.setWidget(self.page_view)
        right_layout.addWidget(self.scroll, 1)

        nav = QHBoxLayout()
        nav.setContentsMargins(12, 8, 12, 8)
        nav.setSpacing(8)
        self.prev_button = QPushButton("Önceki")
        self.prev_button.clicked.connect(lambda: self._go_to(self.page_index - 1))
        nav.addWidget(self.prev_button)
        self.page_label = QLabel("– / –")
        self.page_label.setObjectName("Mono")
        self.page_label.setMinimumWidth(70)
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nav.addWidget(self.page_label)
        self.next_button = QPushButton("Sonraki")
        self.next_button.clicked.connect(lambda: self._go_to(self.page_index + 1))
        nav.addWidget(self.next_button)
        nav.addSpacing(12)
        zoom_out = QPushButton("−")
        zoom_out.setFixedWidth(32)
        zoom_out.clicked.connect(lambda: self._set_zoom(self.zoom - 0.25))
        nav.addWidget(zoom_out)
        self.zoom_label = QLabel("125%")
        self.zoom_label.setObjectName("Mono")
        self.zoom_label.setMinimumWidth(48)
        self.zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nav.addWidget(self.zoom_label)
        zoom_in = QPushButton("+")
        zoom_in.setFixedWidth(32)
        zoom_in.clicked.connect(lambda: self._set_zoom(self.zoom + 0.25))
        nav.addWidget(zoom_in)
        nav.addStretch(1)
        self.status_label = QLabel("")
        self.status_label.setObjectName("Muted")
        nav.addWidget(self.status_label)
        right_layout.addLayout(nav)
        view_layout.addWidget(right, 1)
        root.addWidget(view_panel, 1)

    def _separator(self) -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setStyleSheet("color: #DCD8CF;")
        return line

    def _build_tool_strip(self) -> QFrame:
        strip = QFrame()
        strip.setObjectName("ToolStrip")
        strip.setFixedWidth(104)
        layout = QVBoxLayout(strip)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        group = QButtonGroup(self)
        group.setExclusive(True)
        for key, text, tip in self.TOOLS:
            button = QPushButton(text)
            button.setCheckable(True)
            button.setToolTip(tip)
            button.clicked.connect(lambda _=False, k=key: self._tool_changed(k))
            group.addButton(button)
            layout.addWidget(button)
            self._tool_buttons[key] = button
        self._tool_buttons["select"].setChecked(True)
        layout.addStretch(1)
        return strip

    def _build_page_menu(self) -> None:
        self.page_menu = QMenu(self)
        self.rotate_left_action = self.page_menu.addAction("Sola döndür")
        self.rotate_left_action.triggered.connect(lambda: self._rotate(-90))
        self.rotate_right_action = self.page_menu.addAction("Sağa döndür")
        self.rotate_right_action.triggered.connect(lambda: self._rotate(90))
        self.page_menu.addSeparator()
        self.delete_page_action = self.page_menu.addAction("Sayfayı sil")
        self.delete_page_action.triggered.connect(self._delete_page)
        self.move_page_action = self.page_menu.addAction("Sayfayı taşı…")
        self.move_page_action.triggered.connect(self._move_page)
        self.page_menu.addSeparator()
        self.insert_pdf_action = self.page_menu.addAction("PDF ekle…")
        self.insert_pdf_action.triggered.connect(self._insert_pdf)
        self.split_action = self.page_menu.addAction("Belgeyi böl…")
        self.split_action.triggered.connect(self._split_pdf)
        self.page_menu.addSeparator()
        self.watermark_action = self.page_menu.addAction("Filigran ekle…")
        self.watermark_action.triggered.connect(self._add_watermark)
        self.page_numbers_action = self.page_menu.addAction("Sayfa numarası ekle…")
        self.page_numbers_action.triggered.connect(self._add_page_numbers)
        self.reset_crop_action = self.page_menu.addAction("Kırpmayı sıfırla…")
        self.reset_crop_action.triggered.connect(self._reset_crop)
        self.page_menu.addSeparator()
        self.fill_form_action = self.page_menu.addAction("Form alanlarını doldur…")
        self.fill_form_action.triggered.connect(self._fill_form)
        self.protect_action = self.page_menu.addAction("Şifre ekle…")
        self.protect_action.triggered.connect(self._protect_pdf)
        self.unprotect_action = self.page_menu.addAction("Şifre korumasını kaldır")
        self.unprotect_action.triggered.connect(self._unprotect_pdf)

    def _show_page_menu(self) -> None:
        position = self.page_menu_button.mapToGlobal(
            self.page_menu_button.rect().bottomLeft()
        )
        self.page_menu.popup(position)

    def _set_enabled(self, enabled: bool) -> None:
        for widget in (
            self.save_button,
            self.save_as_button,
            self.undo_button,
            self.redo_button,
            self.page_menu_button,
            self.thumbnails,
            self.prev_button,
            self.next_button,
        ):
            widget.setEnabled(enabled)
        for action in (
            self.rotate_left_action,
            self.rotate_right_action,
            self.delete_page_action,
            self.move_page_action,
            self.insert_pdf_action,
            self.split_action,
            self.watermark_action,
            self.page_numbers_action,
            self.reset_crop_action,
            self.fill_form_action,
            self.protect_action,
            self.unprotect_action,
        ):
            action.setEnabled(enabled)

    def open_path(self, path: str | Path) -> None:
        path = Path(path)
        if self.session is not None:
            if not self._confirm_discard():
                return
            self.session.close()
        try:
            self.session = PdfEditSession(path)
        except PdfPasswordError:
            password, ok = QInputDialog.getText(
                self,
                "Parola gerekli",
                f"{path.name} parola korumalı.\nParolayı girin:",
                QLineEdit.EchoMode.Password,
            )
            if not ok or not password:
                return
            try:
                self.session = PdfEditSession(path, password=password)
            except Exception as exc:  # noqa: BLE001
                QMessageBox.critical(self, "PDF açılamadı", str(exc))
                return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "PDF açılamadı", str(exc))
            return
        self.page_index = 0
        self.file_label.setText(path.name)
        self._set_enabled(True)
        self._refresh_thumbnails()
        self._render()
        self._set_status(f"Açıldı: {self.session.page_count} sayfa")

    def _open_dialog(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "PDF aç", "", "PDF dosyaları (*.pdf)")
        if path:
            self.open_path(path)

    def _confirm_discard(self) -> bool:
        if self.session is None or not self.session.dirty:
            return True
        answer = QMessageBox.question(
            self,
            "Kaydedilmemiş değişiklikler",
            "Kaydedilmemiş değişiklikler var. Devam edilsin mi?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        return answer == QMessageBox.StandardButton.Yes

    def close_session(self) -> None:
        if self.session is not None:
            self.session.close()
            self.session = None
            self._set_enabled(False)
            self._update_undo_buttons()
            self.thumbnails.clear()

    def save_current(self) -> None:
        self._save()

    def can_close(self) -> bool:
        return self._confirm_discard()

    def _render(self) -> None:
        if self.session is None:
            return
        try:
            data = self.session.render(self.page_index, self.zoom)
        except Exception as exc:  # noqa: BLE001
            self._set_status(f"Görüntülenemiyor: {exc}")
            return
        pixmap = QPixmap()
        pixmap.loadFromData(data)
        self.page_view.setPixmap(pixmap)
        self.page_view.resize(pixmap.size())
        self.page_label.setText(f"{self.page_index + 1} / {self.session.page_count}")
        self.zoom_label.setText(f"{int(self.zoom * 100)}%")
        self.prev_button.setEnabled(self.page_index > 0)
        self.next_button.setEnabled(self.page_index < self.session.page_count - 1)
        self._update_undo_buttons()
        self._refresh_current_thumbnail()

    def undo(self) -> None:
        if self.session is None or not self.session.undo():
            return
        self.page_index = max(0, min(self.page_index, self.session.page_count - 1))
        self._refresh_thumbnails()
        self._render()
        self._set_status("Geri alındı")

    def redo(self) -> None:
        if self.session is None or not self.session.redo():
            return
        self.page_index = max(0, min(self.page_index, self.session.page_count - 1))
        self._refresh_thumbnails()
        self._render()
        self._set_status("İleri alındı")

    def _update_undo_buttons(self) -> None:
        has_session = self.session is not None
        self.undo_button.setEnabled(has_session and self.session.can_undo)
        self.redo_button.setEnabled(has_session and self.session.can_redo)

    def _toggle_thumbnails(self, visible: bool) -> None:
        self.thumb_panel.setVisible(visible)

    def _refresh_thumbnails(self) -> None:
        with self.thumbnails.suppress_current():
            self.thumbnails.clear()
            if self.session is None:
                return
            count = self.session.page_count
            shown = min(count, 300)
            for index in range(shown):
                pixmap = QPixmap()
                pixmap.loadFromData(self.session.render_thumbnail(index))
                item = QListWidgetItem(QIcon(pixmap), str(index + 1))
                item.setData(Qt.ItemDataRole.UserRole, index)
                item.setToolTip(f"Sayfa {index + 1}")
                self.thumbnails.addItem(item)
        if count > shown:
            self._set_status(f"Küçük resimler ilk {shown} sayfa için gösteriliyor")
        self._sync_thumbnail_selection()

    def _refresh_current_thumbnail(self) -> None:
        if self.session is None:
            return
        row = self.page_index
        if row >= self.thumbnails.count():
            return
        item = self.thumbnails.item(row)
        if item is None:
            return
        pixmap = QPixmap()
        pixmap.loadFromData(self.session.render_thumbnail(row))
        item.setIcon(QIcon(pixmap))

    def _sync_thumbnail_selection(self) -> None:
        if self.session is None:
            return
        if self.page_index < self.thumbnails.count():
            self.thumbnails.set_current_row_silently(self.page_index)
            item = self.thumbnails.item(self.page_index)
            if item is not None:
                self.thumbnails.scrollToItem(item)

    def _selected_pages(self) -> list[int]:
        rows = self.thumbnails.selected_rows_sorted()
        if not rows:
            return [self.page_index]
        return rows

    def _after_document_change(self) -> None:
        if self.session is None:
            return
        self.page_index = max(0, min(self.page_index, self.session.page_count - 1))
        self._refresh_thumbnails()
        self._render()

    def _on_thumbnails_reordered(self, order: list) -> None:
        if self.session is None:
            return
        try:
            self.session.reorder([int(v) for v in order])
        except ValueError:
            self._refresh_thumbnails()
            return
        self.page_index = max(0, min(self.page_index, self.session.page_count - 1))
        self._render()
        self._sync_thumbnail_selection()
        self._set_status("Sayfalar yeniden sıralandı")

    def _show_thumb_menu(self, global_pos: QPoint) -> None:
        if self.session is None:
            return
        menu = QMenu(self)
        rotate_left = menu.addAction("Sola döndür")
        rotate_right = menu.addAction("Sağa döndür")
        menu.addSeparator()
        duplicate = menu.addAction("Çoğalt")
        copy = menu.addAction("Kopyala")
        cut = menu.addAction("Kes")
        paste = menu.addAction("Yapıştır")
        paste.setEnabled(bool(self._page_clipboard))
        menu.addSeparator()
        delete = menu.addAction("Sil")
        chosen = menu.exec(global_pos)
        if chosen is None:
            return
        if chosen == rotate_left:
            self._rotate_selected(-90)
        elif chosen == rotate_right:
            self._rotate_selected(90)
        elif chosen == duplicate:
            self._duplicate_selected()
        elif chosen == copy:
            self._copy_selected()
        elif chosen == cut:
            self._cut_selected()
        elif chosen == paste:
            self._paste_pages()
        elif chosen == delete:
            self._delete_selected()

    def _rotate_selected(self, delta: int) -> None:
        if self.session is None:
            return
        rows = self._selected_pages()
        self.session.rotate_pages(rows, delta)
        self._after_document_change()
        self._set_status(f"{len(rows)} sayfa döndürüldü")

    def _delete_selected(self) -> None:
        if self.session is None:
            return
        rows = self._selected_pages()
        if len(rows) >= self.session.page_count:
            QMessageBox.information(self, "Silinemez", "Belgede en az bir sayfa kalmalı.")
            return
        answer = QMessageBox.question(
            self,
            "Sayfa sil",
            f"{len(rows)} sayfa silinsin mi?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.session.delete(rows)
        self.page_index = min(self.page_index, self.session.page_count - 1)
        self._after_document_change()
        self._set_status(f"{len(rows)} sayfa silindi")

    def _duplicate_selected(self) -> None:
        if self.session is None:
            return
        rows = self._selected_pages()
        self.session.duplicate_pages(rows)
        self._after_document_change()
        self._set_status(f"{len(rows)} sayfa çoğaltıldı")

    def _copy_selected(self) -> None:
        if self.session is None:
            return
        rows = self._selected_pages()
        self._page_clipboard = self.session.copy_pages(rows)
        self._set_status(f"{len(rows)} sayfa panoya kopyalandı")

    def _cut_selected(self) -> None:
        if self.session is None:
            return
        rows = self._selected_pages()
        if len(rows) >= self.session.page_count:
            QMessageBox.information(self, "Kesilemez", "Belgede en az bir sayfa kalmalı.")
            return
        self._page_clipboard = self.session.copy_pages(rows)
        self.session.delete(rows)
        self.page_index = min(self.page_index, self.session.page_count - 1)
        self._after_document_change()
        self._set_status(f"{len(rows)} sayfa kesildi")

    def _paste_pages(self) -> None:
        if self.session is None or not self._page_clipboard:
            return
        self.session.paste_pages(self._page_clipboard, self.page_index + 1)
        self._after_document_change()
        self._set_status(f"{len(self._page_clipboard)} sayfa yapıştırıldı")

    def _go_to(self, index: int) -> None:
        if self.session is None:
            return
        self.page_index = max(0, min(index, self.session.page_count - 1))
        self.page_view.clear_selection()
        self._render()
        self._sync_thumbnail_selection()

    def _set_zoom(self, zoom: float) -> None:
        self.zoom = max(self.MIN_ZOOM, min(self.MAX_ZOOM, round(zoom, 2)))
        self.page_view.clear_selection()
        self._render()

    def _tool_changed(self, tool: str) -> None:
        self.page_view.set_tool(tool)

    def _rotate(self, delta: int) -> None:
        if self.session is None:
            return
        self.session.rotate(self.page_index, delta)
        self._render()
        self._set_status("Sayfa döndürüldü")

    def _delete_page(self) -> None:
        if self.session is None or self.session.page_count <= 1:
            if self.session is not None:
                QMessageBox.information(self, "Silinemez", "Belgede en az bir sayfa kalmalı.")
            return
        answer = QMessageBox.question(
            self,
            "Sayfa sil",
            f"Sayfa {self.page_index + 1} silinsin mi?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.session.delete([self.page_index])
        self.page_index = min(self.page_index, self.session.page_count - 1)
        self._refresh_thumbnails()
        self._render()
        self._set_status("Sayfa silindi")

    def _move_page(self) -> None:
        if self.session is None:
            return
        target, ok = QInputDialog.getInt(
            self,
            "Sayfayı taşı",
            f"Sayfa {self.page_index + 1} hangi konuma taşınsın?",
            value=self.page_index + 1,
            minValue=1,
            maxValue=self.session.page_count,
        )
        if not ok or target - 1 == self.page_index:
            return
        self.session.move(self.page_index, target - 1)
        self.page_index = target - 1
        self._refresh_thumbnails()
        self._render()
        self._set_status(f"Sayfa {target}. konuma taşındı")

    def _insert_pdf(self) -> None:
        if self.session is None:
            return
        path, _ = QFileDialog.getOpenFileName(self, "Eklenecek PDF", "", "PDF dosyaları (*.pdf)")
        if not path:
            return
        try:
            self.session.insert_from(path, at_index=self.page_index + 1)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Eklenemedi", str(exc))
            return
        self._refresh_thumbnails()
        self._render()
        self._set_status(f"Eklendi: {Path(path).name}")

    def _split_pdf(self) -> None:
        if self.session is None:
            return
        if self.session.dirty:
            QMessageBox.information(
                self,
                "Önce kaydedin",
                "Bölme işlemi kayıtlı dosya üzerinde çalışır. Önce Kaydet'e basın.",
            )
            return
        ranges, ok = QInputDialog.getText(
            self,
            "Belgeyi böl",
            "Aralıklar (her aralık ayrı dosya olur, ör: 1-3;4;5-8):",
        )
        if not ok or not ranges.strip():
            return
        folder = QFileDialog.getExistingDirectory(self, "Çıktı klasörü seç")
        if not folder:
            return
        try:
            outputs = split_pdf(self.session.path, folder, ranges)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Bölme hatası", str(exc))
            return
        self._set_status(f"{len(outputs)} dosyaya bölündü")
        QMessageBox.information(self, "Bölündü", f"{len(outputs)} dosya oluşturuldu.")

    def _save(self) -> None:
        if self.session is None:
            return
        try:
            path = self.session.save()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Kaydedilemedi", str(exc))
            return
        self._set_status(f"Kaydedildi: {path.name}")

    def save_as(self) -> None:
        if self.session is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Farklı kaydet", "", "PDF dosyaları (*.pdf)")
        if not path:
            return
        try:
            saved = self.session.save(path)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Kaydedilemedi", str(exc))
            return
        self.file_label.setText(saved.name)
        self._set_status(f"Kaydedildi: {saved.name}")

    def _on_highlight(self, rect: QRect) -> None:
        if self.session is None:
            return
        pdf_rect = (
            rect.left() / self.zoom,
            rect.top() / self.zoom,
            rect.right() / self.zoom,
            rect.bottom() / self.zoom,
        )
        self.session.add_highlight(self.page_index, pdf_rect)
        self._render()
        self._set_status("Vurgu eklendi")

    def _on_text_click(self, point: QPoint) -> None:
        if self.session is None:
            return
        text, ok = QInputDialog.getMultiLineText(self, "Metin ekle", "Sayfaya eklenecek metin:")
        if not ok or not text.strip():
            return
        try:
            self.session.add_text(
                self.page_index,
                (point.x() / self.zoom, point.y() / self.zoom),
                text,
            )
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Metin eklenemedi", str(exc))
            return
        self._render()
        self._set_status("Metin eklendi")

    def _on_note_click(self, point: QPoint) -> None:
        if self.session is None:
            return
        text, ok = QInputDialog.getMultiLineText(self, "Not ekle", "Yapışkan not içeriği:")
        if not ok or not text.strip():
            return
        self.session.add_note(
            self.page_index,
            (point.x() / self.zoom, point.y() / self.zoom),
            text,
        )
        self._render()
        self._set_status("Not eklendi")

    def _on_selection(self, rect: QRect) -> None:
        if self.session is None:
            return
        box = (
            rect.left() / self.zoom,
            rect.top() / self.zoom,
            (rect.left() + rect.width()) / self.zoom,
            (rect.top() + rect.height()) / self.zoom,
        )
        page = self.session.doc[self.page_index]
        self._selection_text = extract_rect_text(page, box)
        if self._selection_text:
            self._set_status(
                f"Seçildi: {len(self._selection_text)} karakter — Ctrl+C ile kopyalayın"
            )
        else:
            self._set_status("Seçimde metin yok; sayfa taranmış olabilir")

    def _clear_selection(self) -> None:
        self._selection_text = ""
        self._set_status("")

    def copy_selection(self) -> None:
        if not self._selection_text:
            return
        QApplication.clipboard().setText(self._selection_text)
        self._set_status(f"Panoya kopyalandı: {len(self._selection_text)} karakter")

    def _widget_rect_to_pdf(self, rect: QRect) -> tuple[float, float, float, float]:
        return (
            rect.left() / self.zoom,
            rect.top() / self.zoom,
            (rect.left() + rect.width()) / self.zoom,
            (rect.top() + rect.height()) / self.zoom,
        )

    def _on_erase(self, rect: QRect) -> None:
        if self.session is None:
            return
        self.session.whiten(self.page_index, self._widget_rect_to_pdf(rect))
        self._render()
        self._set_status("Alan beyazlatıldı")

    def _on_redact(self, rect: QRect) -> None:
        if self.session is None:
            return
        try:
            self.session.erase_content(self.page_index, self._widget_rect_to_pdf(rect))
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Silinemedi", str(exc))
            return
        self._render()
        self._set_status("İçerik kalıcı olarak silindi")

    def _on_edit(self, rect: QRect) -> None:
        if self.session is None:
            return
        box = self._widget_rect_to_pdf(rect)
        page = self.session.doc[self.page_index]
        old_text = extract_rect_text(page, box)
        if not old_text.strip():
            self._set_status("Seçimde düzenlenebilir metin yok")
            return
        new_text, ok = QInputDialog.getMultiLineText(
            self, "Metni düzenle", "Yeni metin:", old_text
        )
        if not ok or new_text == old_text:
            return
        try:
            self.session.edit_text(self.page_index, box, new_text)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Metin düzenlenemedi", str(exc))
            return
        self._render()
        self._set_status("Metin güncellendi; punto ve renk korundu, font yaklaşıktır")

    def _pick_draw_color(self) -> None:
        color = QColorDialog.getColor(self.draw_color, self, "Çizim rengi")
        if color.isValid():
            self.draw_color = color
            self._apply_color_swatch()

    def _apply_color_swatch(self) -> None:
        c = self.draw_color
        self.color_button.setStyleSheet(
            f"background: rgb({c.red()},{c.green()},{c.blue()});"
            " border: 1px solid #C4BFB4; border-radius: 2px;"
        )

    def _width_changed(self, value: int) -> None:
        self.draw_width = float(value)

    def _draw_color_tuple(self) -> tuple[float, float, float]:
        c = self.draw_color
        return (c.redF(), c.greenF(), c.blueF())

    def _on_pen(self, points: list) -> None:
        if self.session is None or len(points) < 2:
            return
        pdf_points = [(p.x() / self.zoom, p.y() / self.zoom) for p in points]
        self.session.draw_polyline(
            self.page_index, pdf_points, self._draw_color_tuple(), self.draw_width
        )
        self._render()
        self._set_status("Serbest çizim eklendi")

    def _on_shape_rect(self, kind: str, rect: QRect) -> None:
        if self.session is None:
            return
        box = self._widget_rect_to_pdf(rect)
        if kind == "ellipse":
            self.session.draw_ellipse(
                self.page_index, box, self._draw_color_tuple(), self.draw_width
            )
        else:
            self.session.draw_rect(
                self.page_index, box, self._draw_color_tuple(), self.draw_width
            )
        self._render()
        self._set_status("Şekil eklendi")

    def _on_shape_line(self, kind: str, start: QPoint, end: QPoint) -> None:
        if self.session is None or start == end:
            return
        p1 = (start.x() / self.zoom, start.y() / self.zoom)
        p2 = (end.x() / self.zoom, end.y() / self.zoom)
        if kind == "arrow":
            self.session.draw_arrow(
                self.page_index, p1, p2, self._draw_color_tuple(), self.draw_width
            )
            self._set_status("Ok eklendi")
        else:
            self.session.draw_line(
                self.page_index, p1, p2, self._draw_color_tuple(), self.draw_width
            )
            self._set_status("Çizgi eklendi")
        self._render()

    def _resolve_image_source(self) -> dict | None:
        clipboard = QApplication.clipboard()
        if clipboard.mimeData().hasImage():
            image = clipboard.image()
            if not image.isNull():
                buffer = QBuffer()
                buffer.open(QIODevice.OpenModeFlag.WriteOnly)
                if image.save(buffer, "PNG"):
                    return {"data": bytes(buffer.data())}
        path, _ = QFileDialog.getOpenFileName(
            self, "Görsel seç", "", "Görseller (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        if path:
            return {"path": path}
        return None

    def _on_image_rect(self, tool: str, rect: QRect) -> None:
        if self.session is None:
            return
        source = self._resolve_image_source()
        if source is None:
            return
        title = "İmza" if tool == "signature" else "Görsel"
        try:
            self.session.insert_image(
                self.page_index, self._widget_rect_to_pdf(rect), **source
            )
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, f"{title} eklenemedi", str(exc))
            return
        self._render()
        self._set_status(f"{title} eklendi")

    def _target_pages(self, scope: str) -> list[int]:
        if self.session is None:
            return []
        if scope == "all":
            return list(range(self.session.page_count))
        return [self.page_index]

    def _add_watermark(self) -> None:
        if self.session is None:
            return
        dialog = WatermarkDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        values = dialog.values()
        pages = self._target_pages(values["scope"])
        try:
            self.session.add_watermark(
                pages,
                values["text"],
                size=values["size"],
                color=values["color"],
                opacity=values["opacity"],
                angle=values["angle"],
            )
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Filigran eklenemedi", str(exc))
            return
        self._render()
        self._set_status(f"Filigran eklendi ({len(pages)} sayfa)")

    def _add_page_numbers(self) -> None:
        if self.session is None:
            return
        dialog = PageNumberDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        values = dialog.values()
        pages = self._target_pages(values["scope"])
        try:
            self.session.add_page_numbers(
                pages,
                template=values["template"],
                size=values["size"],
                position=values["position"],
                start_number=values["start"],
            )
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Sayfa numarası eklenemedi", str(exc))
            return
        self._render()
        self._set_status(f"Sayfa numarası eklendi ({len(pages)} sayfa)")

    def _crop_scope(self, title: str) -> str | None:
        scope, ok = QInputDialog.getItem(
            self,
            title,
            "Kapsam:",
            ["Geçerli sayfa", "Tüm sayfalar"],
            0,
            False,
        )
        if not ok:
            return None
        return scope

    def _on_crop(self, rect: QRect) -> None:
        if self.session is None:
            return
        page = self.session.doc[self.page_index]
        if page.rotation % 360 != 0:
            QMessageBox.information(
                self,
                "Kırpma",
                "Döndürülmüş sayfada kırpma desteklenmiyor; önce döndürmeyi geri alın.",
            )
            return
        scope = self._crop_scope("Kırpma uygula")
        if scope is None:
            return
        offset = page.cropbox_position
        box = (
            offset.x + rect.left() / self.zoom,
            offset.y + rect.top() / self.zoom,
            offset.x + (rect.left() + rect.width()) / self.zoom,
            offset.y + (rect.top() + rect.height()) / self.zoom,
        )
        try:
            self.session.set_crop(
                self.page_index, box, apply_to_all=(scope == "Tüm sayfalar")
            )
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Kırpılamadı", str(exc))
            return
        self._after_document_change()
        self._set_status("Kırpma uygulandı")

    def _reset_crop(self) -> None:
        if self.session is None:
            return
        scope = self._crop_scope("Kırpmayı sıfırla")
        if scope is None:
            return
        if scope == "Tüm sayfalar":
            self.session.reset_crop(apply_to_all=True)
        else:
            self.session.reset_crop(page_index=self.page_index)
        self._after_document_change()
        self._set_status("Kırpma sıfırlandı")

    def _protect_pdf(self) -> None:
        if self.session is None:
            return
        dialog = PasswordDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        values = dialog.values()
        if not values["user_password"]:
            QMessageBox.warning(self, "Şifre", "Şifre boş olamaz.")
            return
        self.session.set_save_protection(
            values["user_password"],
            values["owner_password"],
            values["allow_print"],
            values["allow_copy"],
        )
        self._set_status("Şifre ayarlandı; Kaydet'e basınca uygulanır")

    def _unprotect_pdf(self) -> None:
        if self.session is None:
            return
        answer = QMessageBox.question(
            self,
            "Korumayı kaldır",
            "Kaydedince şifre koruması kaldırılsın mı?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.session.clear_save_protection()
        self._set_status("Koruma kaldırılacak; Kaydet'e basınca uygulanır")

    def _fill_form(self) -> None:
        if self.session is None:
            return
        fields = self.session.list_form_fields()
        if not fields:
            QMessageBox.information(self, "Form", "Bu belgede form alanı bulunamadı.")
            return
        dialog = FormFillDialog(fields, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        count = self.session.fill_form(dialog.values())
        self._after_document_change()
        self._set_status(f"{count} form alanı dolduruldu")

    def _set_status(self, message: str) -> None:
        self.status_label.setText(message)
