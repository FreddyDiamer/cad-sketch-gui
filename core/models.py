from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Polyline:
    """Простейшее представление контура: полилиния."""

    points: list[tuple[float, float]]


@dataclass(frozen=True)
class Calibration:
    """Калибровка масштаба."""

    real_distance: float
    units: str  # мм/см/м
    x1: int = 0
    y1: int = 0
    x2: int = 0
    y2: int = 0

    @property
    def pixel_distance(self) -> float:
        """Расстояние между опорными точками в пикселях."""
        d = math.hypot(self.x2 - self.x1, self.y2 - self.y1)
        return d if d > 0 else 1.0

    @property
    def scale_mm_per_pixel(self) -> float:
        """Масштаб: миллиметров на пиксель."""
        factor = {"мм": 1.0, "см": 10.0, "м": 1000.0}.get(self.units, 1.0)
        return (self.real_distance * factor) / self.pixel_distance

    @staticmethod
    def default() -> "Calibration":
        return Calibration(real_distance=100.0, units="мм", x1=0, y1=0, x2=100, y2=0)


@dataclass(frozen=True)
class CannyParams:
    """Параметры Canny."""

    low_threshold: int
    high_threshold: int
    gauss_kernel: int = 5
    dp_epsilon: float = 2.0

    @staticmethod
    def default() -> "CannyParams":
        return CannyParams(low_threshold=50, high_threshold=150, gauss_kernel=5, dp_epsilon=2.0)


@dataclass(frozen=True)
class Project:
    name: str
    project_file: Path


@dataclass
class ProjectState:
    """Текущее состояние работы в приложении."""

    project: Project | None = None
    image_path: Path | None = None

    calibration: Calibration | None = None
    canny_params: CannyParams | None = None

    contours: list[Polyline] | None = None
    sketch: dict | None = None

    # Флаг "есть несохранённые изменения" (для UX)
    is_dirty: bool = False
