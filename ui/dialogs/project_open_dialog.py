"""Диалог открытия существующего проекта (.json)."""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QWidget,
    QVBoxLayout,
)


class ProjectOpenDialog(QDialog):
    """Поле ввода пути + кнопка «Выбрать…» (QFileDialog) с фильтром *.json."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Открытие проекта")
        self.setModal(True)

        self._file_edit = QLineEdit()
        self._file_edit.setPlaceholderText("Выберите файл проекта .json…")
        browse_btn = QPushButton("Выбрать…")
        browse_btn.clicked.connect(self._choose_file)

        row = QHBoxLayout()
        row.addWidget(self._file_edit, 1)
        row.addWidget(browse_btn)
        row_widget = QWidget()
        row_widget.setLayout(row)

        form = QFormLayout()
        form.addRow("Файл проекта (.json):", row_widget)

        self._buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self._buttons.accepted.connect(self._on_accept)
        self._buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(self._buttons)
        self.setLayout(layout)

        self._project_file: Path | None = None

    @property
    def project_file(self) -> Path:
        if self._project_file is None:
            raise RuntimeError("Файл проекта не выбран.")
        return self._project_file

    def _choose_file(self) -> None:
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Открыть проект",
            "",
            "Файлы проекта (*.json);;Все файлы (*.*)",
        )
        if file_name:
            self._file_edit.setText(file_name)

    def _on_accept(self) -> None:
        """Проверяет существование файла и корректность расширения."""
        path = Path(self._file_edit.text().strip())
        # Двойная проверка: путь существует и это файл (не каталог).
        if not path.exists() or not path.is_file():
            self._file_edit.setToolTip("Укажите существующий файл проекта")
            self._file_edit.setFocus()
            self._file_edit.selectAll()
            return
        if path.suffix.lower() != ".json":
            self._file_edit.setToolTip("Файл проекта должен быть .json")
            self._file_edit.setFocus()
            self._file_edit.selectAll()
            return
        self._project_file = path
        self.accept()

