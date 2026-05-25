"""Точка входа в подсистему автоматизированного формирования эскизов.

Создаёт QApplication, применяет единый тёмный стиль (см. app/styles.py),
поднимает главное окно и запускает цикл обработки событий Qt.
"""
import sys

from PyQt6.QtWidgets import QApplication

from app.main_window import MainWindow
from app.styles import DARK_QSS


def main() -> int:
    app = QApplication(sys.argv)
    # Имена нужны Qt для сохранения настроек (QSettings) в системном
    # реестре/конфиге — без них настройки попадают в безымянный раздел.
    app.setOrganizationName("Подсистема эскизов")
    app.setApplicationName("Подсистема формирования эскизов")
    # «Fusion» — единая стилистическая база для QSS на всех платформах:
    # Windows/macOS/Linux выглядят одинаково и одинаково реагируют на QSS.
    app.setStyle("Fusion")
    # Глобальный тёмный стиль применяется один раз ко всему приложению.
    app.setStyleSheet(DARK_QSS)

    window = MainWindow()
    window.show()

    # exec() возвращает код завершения, который пробрасываем в SystemExit.
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
