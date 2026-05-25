"""Диалог создания нового проекта.

Запрашивает у пользователя имя проекта и папку. Имя файла .json
формируется автоматически из имени проекта (с заменой недопустимых
для файловой системы символов на «_»).
"""
from __future__ import annotations

import re
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
    QWidget,
    QVBoxLayout,
)


class ProjectCreateDialog(QDialog):
    """Модальный диалог: имя проекта + папка сохранения + кнопки OK/Отмена."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Создание проекта")
        self.setModal(True)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("Например: Деталь_001")
        self._dir_edit = QLineEdit()
        self._dir_edit.setReadOnly(True)
        self._dir_edit.setPlaceholderText("Выберите папку…")

        browse_btn = QPushButton("Выбрать…")
        browse_btn.clicked.connect(self._choose_dir)

        dir_row = QHBoxLayout()
        dir_row.addWidget(self._dir_edit, 1)
        dir_row.addWidget(browse_btn)
        dir_widget = QWidget()
        dir_widget.setLayout(dir_row)

        form = QFormLayout()
        form.addRow("Название проекта:", self._name_edit)
        form.addRow("Папка проекта:", dir_widget)

        self._buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self._buttons.accepted.connect(self._on_accept)
        self._buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(self._buttons)
        self.setLayout(layout)

        self._project_file: Path | None = None

    @property
    def project_name(self) -> str:
        return self._name_edit.text().strip()

    @property
    def project_file(self) -> Path:
        if self._project_file is None:
            raise RuntimeError("Файл проекта ещё не сформирован.")
        return self._project_file

    def _choose_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Выберите папку проекта")
        if directory:
            self._dir_edit.setText(directory)

    def _on_accept(self) -> None:
        """Валидация ввода и формирование пути к файлу проекта."""
        name = self.project_name
        directory = self._dir_edit.text().strip()

        # Пустое имя — фокус возвращаем в поле, без закрытия диалога.
        if not name:
            self._name_edit.setFocus()
            self._name_edit.selectAll()
            self._name_edit.setToolTip("Введите название проекта")
            return
        if not directory:
            self._dir_edit.setToolTip("Выберите папку проекта")
            return

        # Безопасное имя файла: заменяем всё, кроме букв/цифр/«_»/«-», на «_».
        safe = re.sub(r"[^0-9A-Za-zА-Яа-я_-]+", "_", name).strip("_")
        if not safe:
            # Подстраховка: если имя состояло только из спецсимволов.
            safe = "проект"
        self._project_file = Path(directory) / f"{safe}.json"
        self.accept()

