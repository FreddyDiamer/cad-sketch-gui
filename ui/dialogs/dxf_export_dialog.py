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
    QWidget,
    QVBoxLayout,
)


class DxfExportDialog(QDialog):
    def __init__(self, project_name: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Экспорт DXF")
        self.setModal(True)

        self._default_name = f"{project_name}.dxf" if project_name else "sketch.dxf"

        self._file_edit = QLineEdit()
        self._file_edit.setText(self._default_name)
        self._file_edit.setPlaceholderText(f"Например: {self._default_name}")
        browse_btn = QPushButton("Выбрать…")
        browse_btn.clicked.connect(self._choose_file)

        row = QHBoxLayout()
        row.addWidget(self._file_edit, 1)
        row.addWidget(browse_btn)
        row_widget = QWidget()
        row_widget.setLayout(row)

        form = QFormLayout()
        form.addRow(QLabel("Проект:"), QLabel(project_name))
        form.addRow("Файл DXF:", row_widget)

        self._buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self._buttons.accepted.connect(self._on_accept)
        self._buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(self._buttons)
        self.setLayout(layout)

        self._target_file: Path | None = None

    @property
    def target_file(self) -> Path:
        if self._target_file is None:
            raise RuntimeError("Файл экспорта не выбран.")
        return self._target_file

    def _choose_file(self) -> None:
        # Используем то, что уже введено в поле, как стартовое имя/путь —
        # пользователь увидит привычное «<имя_проекта>.dxf» в системном диалоге.
        start = self._file_edit.text().strip() or self._default_name
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Экспорт DXF",
            start,
            "DXF (*.dxf)",
        )
        if file_name:
            self._file_edit.setText(file_name)

    def _on_accept(self) -> None:
        raw = self._file_edit.text().strip()
        if not raw:
            self._file_edit.setToolTip("Укажите путь к файлу .dxf")
            self._file_edit.setFocus()
            return
        path = Path(raw)
        if path.suffix.lower() != ".dxf":
            path = path.with_suffix(".dxf")
            self._file_edit.setText(str(path))
        self._target_file = path
        self.accept()

