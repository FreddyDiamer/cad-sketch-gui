import sys

from PyQt6.QtWidgets import QApplication

from app.main_window import MainWindow
from app.styles import DARK_QSS


def main() -> int:
    app = QApplication(sys.argv)
    app.setOrganizationName("CADSketchGUI")
    app.setApplicationName("CAD Sketch GUI")
    app.setStyle("Fusion")  # единообразная база для QSS на всех платформах
    app.setStyleSheet(DARK_QSS)

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
