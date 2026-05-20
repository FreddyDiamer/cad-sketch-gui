from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget


class WelcomeWidget(QWidget):
    """Стартовый экран, когда проекта ещё нет."""

    createRequested = pyqtSignal()
    openRequested = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        title = QLabel("Нет открытого проекта")
        title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        title.setStyleSheet("font-size: 18px; font-weight: 600;")

        hint = QLabel(
            "Создайте новый проект или откройте существующий.\n"
            "После этого станет доступен импорт изображения и дальнейшие шаги."
        )
        hint.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        hint.setWordWrap(True)

        btn_create = QPushButton("Создать проект…")
        btn_create.setMinimumHeight(40)
        btn_create.clicked.connect(self.createRequested.emit)

        btn_open = QPushButton("Открыть проект…")
        btn_open.setMinimumHeight(40)
        btn_open.clicked.connect(self.openRequested.emit)

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(12)
        layout.addWidget(title)
        layout.addWidget(hint)
        layout.addSpacing(8)
        layout.addWidget(btn_create)
        layout.addWidget(btn_open)
        self.setLayout(layout)

