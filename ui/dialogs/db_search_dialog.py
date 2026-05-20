from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QVBoxLayout,
)


class DbSearchDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Поиск в БД")
        self.setModal(True)

        self._query = QLineEdit()

        form = QFormLayout()
        form.addRow("Запрос / ключ:", self._query)

        self._buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self._buttons.accepted.connect(self._on_accept)
        self._buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(self._buttons)
        self.setLayout(layout)

    @property
    def query(self) -> str:
        return self._query.text().strip()

    def _on_accept(self) -> None:
        if not self.query:
            self._query.setFocus()
            return
        self.accept()

