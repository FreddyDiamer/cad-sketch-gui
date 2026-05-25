"""Загрузка растрового изображения в формате QImage."""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtGui import QImage


class ImageLoader:
    """Тонкая обёртка над QImage с проверкой формата файла."""

    @staticmethod
    def load(path: Path) -> QImage:
        """Загружает изображение и возвращает QImage.

        Векторный формат SVG не поддерживается — алгоритм Canny работает
        с растром. PNG, JPG, BMP, TIFF читаются штатно средствами Qt.
        """
        if path.suffix.lower() == ".svg":
            raise ValueError("SVG не поддерживается.")
        image = QImage(str(path))
        # QImage возвращает «нулевое» изображение, если файл повреждён
        # или формат не поддерживается — это явный признак ошибки.
        if image.isNull():
            raise ValueError("Не удалось прочитать изображение.")
        return image
