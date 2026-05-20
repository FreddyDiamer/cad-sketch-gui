from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)


class DbConnectDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Подключение к БД")
        self.setModal(True)

        self._host = QLineEdit()
        self._host.setPlaceholderText("localhost")
        self._db = QLineEdit()
        self._db.setPlaceholderText("cad_db")
        self._user = QLineEdit()
        self._user.setPlaceholderText("user")
        self._password = QLineEdit()
        self._password.setEchoMode(QLineEdit.EchoMode.Password)

        hint = QLabel("Для SQLite: укажите путь к файлу, например: /Users/.../sketch_db.sqlite")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: gray; font-size: 11px;")

        form = QFormLayout()
        form.addRow("Хост:", self._host)
        form.addRow("База данных:", self._db)
        form.addRow("", hint)
        form.addRow("Пользователь:", self._user)
        form.addRow("Пароль:", self._password)

        self._buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self._buttons.accepted.connect(self._on_accept)
        self._buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(self._buttons)
        self.setLayout(layout)

    @property
    def host(self) -> str:
        return self._host.text().strip()

    @property
    def database(self) -> str:
        return self._db.text().strip()

    @property
    def user(self) -> str:
        return self._user.text().strip()

    @property
    def password(self) -> str:
        return self._password.text()

    def _on_accept(self) -> None:
        if not self.host:
            self._host.setFocus()
            return
        if not self.database:
            self._db.setFocus()
            return
        self.accept()

