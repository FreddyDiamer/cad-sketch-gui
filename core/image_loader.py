from __future__ import annotations

from pathlib import Path

from PyQt6.QtGui import QImage


class ImageLoader:
    """Загрузка изображения."""

    @staticmethod
    def load(path: Path) -> QImage:
        if path.suffix.lower() == ".svg":
            raise ValueError("SVG не поддерживается.")
        image = QImage(str(path))
        if image.isNull():
            raise ValueError("Не удалось прочитать изображение.")
        return image

