from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

_TRUTHY = {"1", "true", "evet", "yes", "x", "✓", "on"}


class PasswordDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Şifre ekle")
        form = QFormLayout(self)

        self.user_edit = QLineEdit()
        self.user_edit.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Şifre", self.user_edit)

        self.owner_edit = QLineEdit()
        self.owner_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.owner_edit.setPlaceholderText("Boşsa şifre ile aynı")
        form.addRow("Sahip şifresi", self.owner_edit)

        self.print_check = QCheckBox("Yazdırmaya izin ver")
        self.print_check.setChecked(True)
        form.addRow("", self.print_check)

        self.copy_check = QCheckBox("Kopyalamaya izin ver")
        self.copy_check.setChecked(True)
        form.addRow("", self.copy_check)

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
            "user_password": self.user_edit.text(),
            "owner_password": self.owner_edit.text(),
            "allow_print": self.print_check.isChecked(),
            "allow_copy": self.copy_check.isChecked(),
        }


class FormFillDialog(QDialog):
    def __init__(self, fields: list[dict], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Form alanlarını doldur")
        form = QFormLayout(self)
        self._editors: dict[str, QWidget] = {}

        for field in fields:
            label = f"{field['name']} (sayfa {field['page'] + 1}, {field['type']})"
            editor = self._make_editor(field)
            form.addRow(label, editor)
            self._editors[field["name"]] = editor

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout()
        layout.addWidget(buttons)
        form.addRow(layout)

    def _make_editor(self, field: dict) -> QWidget:
        value = field.get("value")
        if field["type"] == "Onay kutusu":
            editor = QCheckBox()
            editor.setChecked(str(value or "").strip().lower() in _TRUTHY)
            return editor
        if field["type"] in ("Açılır liste", "Liste") and field.get("choices"):
            editor = QComboBox()
            editor.addItems([str(c) for c in field["choices"]])
            if value is not None:
                index = editor.findText(str(value))
                if index >= 0:
                    editor.setCurrentIndex(index)
            return editor
        editor = QLineEdit("" if value is None else str(value))
        return editor

    def values(self) -> dict:
        result: dict[str, str] = {}
        for name, editor in self._editors.items():
            if isinstance(editor, QCheckBox):
                result[name] = "Evet" if editor.isChecked() else ""
            elif isinstance(editor, QComboBox):
                result[name] = editor.currentText()
            else:
                result[name] = editor.text()
        return result
