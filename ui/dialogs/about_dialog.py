from __future__ import annotations

from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout


class AboutDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("О программе")
        self.setModal(True)

        text = QLabel(
            "Подсистема автоматизированного формирования эскизов деталей по изображениям\n"
            "Приложение предназначено для загрузки изображения, обработки и формирования эскиза.\n"
            "Поддерживается экспорт эскиза в формат DXF."
        )
        text.setWordWrap(True)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)

        layout = QVBoxLayout()
        layout.addWidget(text)
        layout.addWidget(buttons)
        self.setLayout(layout)

