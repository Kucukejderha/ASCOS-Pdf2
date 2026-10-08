from __future__ import annotations

from contextlib import contextmanager

from PySide6.QtCore import QPoint, QSize, Qt, Signal
from PySide6.QtWidgets import QListWidget, QWidget


class ThumbnailList(QListWidget):
    """Sayfa küçük resimleri; sürükle-bırak ile sıralama, çoklu seçim."""

    order_changed = Signal(list)
    page_activated = Signal(int)
    context_menu_requested = Signal(QPoint)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setViewMode(QListWidget.ViewMode.IconMode)
        self.setIconSize(QSize(96, 128))
        self.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.setMovement(QListWidget.Movement.Static)
        self.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.setSpacing(4)
        self.setWordWrap(False)
        self._suppress_current = False
        self.currentRowChanged.connect(self._on_current_row_changed)

    def _on_current_row_changed(self, row: int) -> None:
        if not self._suppress_current and row >= 0:
            self.page_activated.emit(row)

    def dropEvent(self, event) -> None:  # noqa: ANN001
        super().dropEvent(event)
        order = [
            self.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.count())
        ]
        if all(isinstance(v, int) for v in order):
            self.order_changed.emit(order)

    def contextMenuEvent(self, event) -> None:  # noqa: ANN001
        self.context_menu_requested.emit(event.globalPos())

    def selected_rows_sorted(self) -> list[int]:
        return sorted(index.row() for index in self.selectedIndexes())

    def set_current_row_silently(self, row: int) -> None:
        self._suppress_current = True
        try:
            self.setCurrentRow(row)
        finally:
            self._suppress_current = False

    @contextmanager
    def suppress_current(self):
        """Doldurma/silme sırasında oluşan currentRowChanged sinyallerini bastırır."""
        self._suppress_current = True
        try:
            yield
        finally:
            self._suppress_current = False
