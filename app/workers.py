from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal
from app.core.models import ConversionOptions, ConversionResult
from app.core.pipeline import convert


class ConversionWorker(QObject):
    """Birden fazla PDF'i sırayla dönüştürür; sinyallerle UI'yi besler."""

    progress = Signal(int, float, str)
    finished = Signal(int, object)
    failed = Signal(int, str)
    all_done = Signal()

    def __init__(
        self,
        files: list[Path],
        options: ConversionOptions,
        output_dir: Path | None = None,
    ) -> None:
        super().__init__()
        self._files = files
        self._options = options
        self._output_dir = output_dir
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        for index, src in enumerate(self._files):
            if self._cancelled:
                break
            try:
                result: ConversionResult = convert(
                    src,
                    self._options,
                    output_dir=self._output_dir,
                    progress=lambda fraction, message, i=index: self.progress.emit(
                        i, fraction, message
                    ),
                )
            except Exception as exc:  # noqa: BLE001 - kullanıcıya mesaj olarak iletilir
                self.failed.emit(index, str(exc))
                continue
            self.finished.emit(index, result)
        self.all_done.emit()


def start_worker(worker: ConversionWorker, parent: QObject | None = None) -> QThread:
    """Worker'ı bir QThread'e taşır.

    Thread'e parent verilmezse Python referansı düşene kadar yaşamalıdır;
    parent verilmesi yaşam döngüsünü Qt'ye bağlar ve erken yok edilmeyi önler.
    """
    thread = QThread(parent)
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    worker.all_done.connect(thread.quit)
    thread.finished.connect(worker.deleteLater)
    thread.finished.connect(thread.deleteLater)
    return thread
