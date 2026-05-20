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
        if not self.record_id:
            self._id.setFocus()
            return
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

