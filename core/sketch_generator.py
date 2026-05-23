from __future__ import annotations

from core.models import Calibration, Circle, Polyline


class SketchGenerator:
    """Формирование эскиза. Применяет масштаб калибровки (мм/пиксель)."""

    def build(
        self,
        contours: list[Polyline | Circle],
        calibration: Calibration | None = None,
    ) -> dict:
        # Эскиз хранится в пиксельных координатах, чтобы корректно отображаться
        # поверх изображения в WorkspaceView. Масштабирование в миллиметры
        # выполняется только при экспорте DXF, используя сохранённый scale.
        scale = calibration.scale_mm_per_pixel if calibration is not None else 1.0
        if scale <= 0:
            scale = 1.0
        return {"entities": list(contours), "scale": scale}
