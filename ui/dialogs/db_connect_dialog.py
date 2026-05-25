"""Диалог подключения к базе данных (SQLite).

Поскольку используется встраиваемая СУБД SQLite, подключение
сводится к выбору файла базы. Хост, имя пользователя и пароль не
требуются. Если указанного файла нет, он будет создан при подключении.
"""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class DbConnectDialog(QDialog):
    """Диалог подключения к базе данных SQLite (выбор файла)."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Подключение к базе данных")
        self.setModal(True)

        self._file_edit = QLineEdit()
        self._file_edit.setPlaceholderText("Например: sketch_db.sqlite")
        self._file_edit.setText("sketch_db.sqlite")

        browse_btn = QPushButton("Выбрать…")
        browse_btn.clicked.connect(self._choose_file)

        row = QHBoxLayout()
        row.addWidget(self._file_edit, 1)
        row.addWidget(browse_btn)
        row_widget = QWidget()
        row_widget.setLayout(row)

        hint = QLabel(
            "Подсистема использует встраиваемую СУБД SQLite. "
            "Укажите путь к файлу базы данных; если файла нет, он будет создан."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #8b949e; font-size: 11px;")

        form = QFormLayout()
        form.addRow("Файл базы данных:", row_widget)
        form.addRow("", hint)

        self._buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self._buttons.accepted.connect(self._on_accept)
        self._buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(self._buttons)
        self.setLayout(layout)

    @property
    def database(self) -> str:
        return self._file_edit.text().strip()

    def _choose_file(self) -> None:
        start = self._file_edit.text().strip() or "sketch_db.sqlite"
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Выберите файл базы данных",
            start,
            "SQLite (*.sqlite *.db);;Все файлы (*)",
        )
        if file_name:
            path = Path(file_name)
            if path.suffix.lower() not in (".sqlite", ".db"):
                path = path.with_suffix(".sqlite")
            self._file_edit.setText(str(path))

    def _on_accept(self) -> None:
        if not self.database:
            self._file_edit.setFocus()
            self._file_edit.setToolTip("Укажите путь к файлу базы данных")
            return
        self.accept()
