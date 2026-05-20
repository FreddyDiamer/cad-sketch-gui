from __future__ import annotations

from pathlib import Path

import cv2

from core.models import CannyParams, Polyline


class ContourDetector:
    """Выделение контуров через Canny + Douglas–Peucker."""

    def detect(self, image_path: Path, params: CannyParams) -> list[Polyline]:
        img = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError(f"Не удалось прочитать изображение: {image_path}")

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        k = max(3, int(params.gauss_kernel) | 1)
        blurred = cv2.GaussianBlur(gray, (k, k), 0)

        edges = cv2.Canny(blurred, int(params.low_threshold), int(params.high_threshold))

        contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)

        eps = max(0.1, float(params.dp_epsilon))
        result: list[Polyline] = []
        for contour in contours:
            approx = cv2.approxPolyDP(contour, eps, closed=True)
            pts: list[tuple[float, float]] = [
                (float(p[0][0]), float(p[0][1])) for p in approx
            ]
            if len(pts) < 3:
                continue
            if pts[0] != pts[-1]:
                pts.append(pts[0])
            result.append(Polyline(points=pts))

        return result
