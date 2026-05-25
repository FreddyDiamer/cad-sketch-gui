"""Диалог удаления записи из БД по ID с подтверждением."""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
)


class DbDeleteDialog(QDialog):
    """Поле ввода ID + двухступенчатое подтверждение перед удалением."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Удаление из БД")
        self.setModal(True)

        self._id = QLineEdit()
        self._id.setPlaceholderText("Например: 123")

        form = QFormLayout()
        form.addRow("ID записи:", self._id)

        self._buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self._buttons.accepted.connect(self._on_accept)
        self._buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(self._buttons)
        self.setLayout(layout)

    @property
    def record_id(self) -> str:
        return self._id.text().strip()

    def _on_accept(self) -> None:
        """Дополнительный диалог подтверждения — защита от случайного клика."""
        if not self.record_id:
            self._id.setFocus()
            return
        # Удаление каскадно зачищает связанные записи (см. database_operations.py),
        # поэтому требуем явного подтверждения.
        answer = QMessageBox.question(
            self,
            "Подтверждение",
            "Удалить запись? Операция необратима.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.accept()

