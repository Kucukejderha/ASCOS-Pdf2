from __future__ import annotations

from PySide6.QtCore import QByteArray, QSettings


class SettingsStore:
    """Kullanıcı tercihlerini QSettings üzerinden saklar (Windows'ta kayıt defteri)."""

    def __init__(self) -> None:
        self._s = QSettings("Pdf2", "Pdf2")

    def get_str(self, key: str, default: str = "") -> str:
        value = self._s.value(key, default)
        return str(value) if value is not None else default

    def set_str(self, key: str, value: str) -> None:
        self._s.setValue(key, value)

    def get_bool(self, key: str, default: bool = False) -> bool:
        value = self._s.value(key, default)
        if isinstance(value, bool):
            return value
        return str(value).lower() in {"1", "true", "yes"}

    def set_bool(self, key: str, value: bool) -> None:
        self._s.setValue(key, value)

    def get_bytes(self, key: str) -> QByteArray:
        value = self._s.value(key)
        return value if isinstance(value, QByteArray) else QByteArray()

    def set_bytes(self, key: str, value: QByteArray) -> None:
        self._s.setValue(key, value)

    def sync(self) -> None:
        self._s.sync()
