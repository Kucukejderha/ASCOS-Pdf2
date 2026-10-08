from __future__ import annotations

from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


def _make_color_button(dialog: QDialog, initial: QColor) -> QPushButton:
    button = QPushButton("")
    button.setFixedSize(28, 22)
    button.setProperty("selected_color", initial.name())

    def apply(color: QColor) -> None:
        button.setProperty("selected_color", color.name())
        button.setStyleSheet(
            f"background: {color.name()}; border: 1px solid #C4BFB4; border-radius: 2px;"
        )

    def pick() -> None:
        color = QColorDialog.getColor(
            QColor(str(button.property("selected_color"))), dialog, "Renk seç"
        )
        if color.isValid():
            apply(color)

    button.clicked.connect(pick)
    apply(initial)
    return button


def _scope_combo() -> QComboBox:
    combo = QComboBox()
    combo.addItem("Tüm sayfalar", "all")
    combo.addItem("Geçerli sayfa", "current")
    return combo


class WatermarkDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Filigran ekle")
        form = QFormLayout(self)

        self.text_edit = QLineEdit("TASLAK")
        form.addRow("Metin", self.text_edit)

        self.size_spin = QSpinBox()
        self.size_spin.setRange(12, 160)
        self.size_spin.setValue(48)
        form.addRow("Punto", self.size_spin)

        self.color_button = _make_color_button(self, QColor("#B4B4B4"))
        form.addRow("Renk", self.color_button)

        self.opacity_spin = QSpinBox()
        self.opacity_spin.setRange(5, 100)
        self.opacity_spin.setSingleStep(5)
        self.opacity_spin.setValue(30)
        self.opacity_spin.setSuffix(" %")
        form.addRow("Opaklık", self.opacity_spin)

        self.angle_combo = QComboBox()
        for label, value in (("45°", 45), ("0°", 0), ("90°", 90), ("-45°", -45)):
            self.angle_combo.addItem(label, value)
        form.addRow("Açı", self.angle_combo)

        self.scope_combo = _scope_combo()
        form.addRow("Uygulama", self.scope_combo)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout()
        layout.addWidget(buttons)
        form.addRow(layout)

    def values(self) -> dict:
        color = QColor(str(self.color_button.property("selected_color")))
        return {
            "text": self.text_edit.text(),
            "size": float(self.size_spin.value()),
            "color": (color.redF(), color.greenF(), color.blueF()),
            "opacity": self.opacity_spin.value() / 100,
            "angle": float(self.angle_combo.currentData()),
            "scope": self.scope_combo.currentData(),
        }


class PageNumberDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Sayfa numarası ekle")
        form = QFormLayout(self)

        self.template_edit = QLineEdit("Sayfa {n} / {total}")
        self.template_edit.setToolTip("{n} numara, {total} toplam sayfa sayısıdır")
        form.addRow("Şablon", self.template_edit)

        self.size_spin = QSpinBox()
        self.size_spin.setRange(7, 24)
        self.size_spin.setValue(9)
        form.addRow("Punto", self.size_spin)

        self.position_combo = QComboBox()
        self.position_combo.addItem("Alt orta", "bottom-center")
        self.position_combo.addItem("Alt sağ", "bottom-right")
        self.position_combo.addItem("Üst orta", "top-center")
        form.addRow("Konum", self.position_combo)

        self.start_spin = QSpinBox()
        self.start_spin.setRange(1, 9999)
        self.start_spin.setValue(1)
        form.addRow("Başlangıç no", self.start_spin)

        self.scope_combo = _scope_combo()
        form.addRow("Uygulama", self.scope_combo)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout()
        layout.addWidget(buttons)
        form.addRow(layout)

    def values(self) -> dict:
        return {
            "template": self.template_edit.text(),
            "size": float(self.size_spin.value()),
            "position": self.position_combo.currentData(),
            "start": self.start_spin.value(),
            "scope": self.scope_combo.currentData(),
        }
