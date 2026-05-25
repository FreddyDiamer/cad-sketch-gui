"""Доменные модели подсистемы.

В модуле собраны неизменяемые (frozen) датаклассы, которые передаются
между слоями (ядро, интерфейс, операции с файлами и БД). Использование
frozen-датаклассов исключает случайную мутацию данных и упрощает отладку.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Polyline:
    """Замкнутая или открытая ломаная — последовательность точек контура.

    Координаты хранятся в пикселях исходного изображения. Перевод в
    миллиметры выполняется при экспорте DXF с использованием калибровки.
    """

    points: list[tuple[float, float]]


@dataclass(frozen=True)
class Circle:
    """Окружность как самостоятельный геометрический примитив.

    Выделяется отдельно от ломаных, чтобы при экспорте в DXF сохранить
    её именно как примитив CIRCLE, а не как многоугольник.
    """

    cx: float        # координата X центра, пиксели
    cy: float        # координата Y центра, пиксели
    radius: float    # радиус, пиксели


@dataclass(frozen=True)
class Calibration:
    """Двухточечная калибровка масштаба изображения.

    Хранит координаты двух опорных точек (в пикселях) и реальное
    расстояние между ними. Масштабный коэффициент мм/пиксель
    вычисляется на лету через свойство `scale_mm_per_pixel`.
    """

    real_distance: float   # реальное расстояние между опорными точками
    units: str             # единицы измерения: «мм», «см» или «м»
    # Координаты двух опорных точек в пикселях изображения.
    x1: int = 0
    y1: int = 0
    x2: int = 0
    y2: int = 0

    @property
    def pixel_distance(self) -> float:
        """Расстояние между опорными точками в пикселях (Евклид)."""
        d = math.hypot(self.x2 - self.x1, self.y2 - self.y1)
        # Защита от деления на ноль, если точки совпали.
        return d if d > 0 else 1.0

    @property
    def scale_mm_per_pixel(self) -> float:
        """Масштабный коэффициент: сколько миллиметров приходится на пиксель.

        Учитывает выбранные пользователем единицы, приводя их к миллиметрам.
        """
        factor = {"мм": 1.0, "см": 10.0, "м": 1000.0}.get(self.units, 1.0)
        return (self.real_distance * factor) / self.pixel_distance

    @staticmethod
    def default() -> "Calibration":
        """Значения по умолчанию (используются как fallback при экспорте)."""
        return Calibration(real_distance=100.0, units="мм", x1=0, y1=0, x2=100, y2=0)


@dataclass(frozen=True)
class CannyParams:
    """Набор параметров алгоритма Canny и аппроксимации Дугласа–Пёкера."""

    low_threshold: int          # нижний порог Canny (0–255)
    high_threshold: int         # верхний порог Canny (0–255)
    gauss_kernel: int = 5       # размер ядра Гаусса (нечётный)
    dp_epsilon: float = 2.0     # допуск аппроксимации Дугласа–Пёкера, пиксели

    @staticmethod
    def default() -> "CannyParams":
        """Рекомендуемые значения параметров по умолчанию."""
        return CannyParams(low_threshold=50, high_threshold=150, gauss_kernel=5, dp_epsilon=2.0)


@dataclass(frozen=True)
class Project:
    """Описание проекта: имя и путь к файлу описания (.json)."""

    name: str
    project_file: Path


@dataclass
class ProjectState:
    """Текущее состояние сеанса работы с приложением.

    Содержит все данные, необходимые для отображения интерфейса и
    выполнения операций: открытый проект, импортированное изображение,
    калибровка, параметры Canny, найденные контуры и построенный эскиз.
    Класс не frozen, потому что состояние меняется в ходе работы.
    """

    project: Project | None = None
    image_path: Path | None = None

    calibration: Calibration | None = None
    canny_params: CannyParams | None = None

    contours: list[Polyline] | None = None    # результат выделения контуров
    sketch: dict | None = None                # построенный эскиз (entities + scale)

    # Признак наличия несохранённых изменений (для подсказки пользователю).
    is_dirty: bool = False
