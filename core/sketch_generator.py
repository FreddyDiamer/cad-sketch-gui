from __future__ import annotations

from core.models import Calibration, Polyline


class SketchGenerator:
    """Формирование эскиза. Применяет масштаб калибровки (мм/пиксель)."""

    def build(self, contours: list[Polyline], calibration: Calibration | None = None) -> dict:
        scale = calibration.scale_mm_per_pixel if calibration is not None else 1.0
        if scale <= 0:
            scale = 1.0

        if scale == 1.0:
            scaled = list(contours)
        else:
            scaled = [
                Polyline(points=[(x * scale, y * scale) for x, y in poly.points])
                for poly in contours
            ]

        return {"entities": scaled, "scale": scale}
