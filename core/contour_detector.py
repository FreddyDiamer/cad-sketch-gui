from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from core.models import CannyParams, Polyline


class ContourDetector:
    """Выделение контуров через Canny + морфологическое слияние + Douglas–Peucker."""

    def detect(self, image_path: Path, params: CannyParams) -> list[Polyline]:
        img = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError(f"Не удалось прочитать изображение: {image_path}")

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        k = max(3, int(params.gauss_kernel) | 1)
        blurred = cv2.GaussianBlur(gray, (k, k), 0)

        edges = cv2.Canny(blurred, int(params.low_threshold), int(params.high_threshold))

        # Сливаем две стороны одного штриха в одну сплошную полосу: dilate утолщает
        # края Canny так, что параллельные грани одного штриха слипаются в одну фигуру.
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        merged = cv2.dilate(edges, kernel, iterations=2)

        # Берём все контуры с иерархией: внешние + дыры. Затем фильтруем дыры-«двойники»
        # (когда дыра занимает почти всю площадь родителя — это просто внутренний край
        # того же утолщённого штриха, а не настоящее отверстие в детали).
        contours, hierarchy = cv2.findContours(merged, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
        keep_mask = [True] * len(contours)
        if hierarchy is not None:
            for i, cnt in enumerate(contours):
                parent = int(hierarchy[0][i][3])
                if parent < 0:
                    continue
                px, py, pw, ph = cv2.boundingRect(contours[parent])
                hx, hy, hw, hh = cv2.boundingRect(cnt)
                # Если дыра по габаритам близка к родителю — это внутренний край того
                # же штриха (двойник). Настоящее отверстие сильно меньше по габаритам.
                if pw > 0 and ph > 0 and (hw / pw) > 0.6 and (hh / ph) > 0.6:
                    keep_mask[i] = False

        eps = max(0.1, float(params.dp_epsilon))
        result: list[Polyline] = []
        for i, contour in enumerate(contours):
            if not keep_mask[i]:
                continue
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
