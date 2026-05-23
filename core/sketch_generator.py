from __future__ import annotations

from core.models import Calibration, Circle, Polyline


class SketchGenerator:
    """Формирование эскиза. Применяет масштаб калибровки (мм/пиксель)."""

    def build(
        self,
        contours: list[Polyline | Circle],
        calibration: Calibration | None = None,
    ) -> dict:
        scale = calibration.scale_mm_per_pixel if calibration is not None else 1.0
        if scale <= 0:
            scale = 1.0

        if scale == 1.0:
            scaled = list(contours)
        else:
            scaled = []
            for ent in contours:
                if isinstance(ent, Circle):
                    scaled.append(
                        Circle(cx=ent.cx * scale, cy=ent.cy * scale, radius=ent.radius * scale)
                    )
                else:
                    scaled.append(
                        Polyline(points=[(x * scale, y * scale) for x, y in ent.points])
                    )

        return {"entities": scaled, "scale": scale}
