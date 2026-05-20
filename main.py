import sys

from PyQt6.QtWidgets import QApplication

from app.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setOrganizationName("CADSketchGUI")
    app.setApplicationName("CAD Sketch GUI")

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

