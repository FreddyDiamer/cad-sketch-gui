from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from core.models import CannyParams, Circle, Polyline


class ContourDetector:
    """Выделение контуров через Canny + морфологическое слияние + Douglas–Peucker.

    Контуры, близкие к окружности, возвращаются как объекты Circle.
    """

    def detect(self, image_path: Path, params: CannyParams) -> list[Polyline | Circle]:
        img = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError(f"Не удалось прочитать изображение: {image_path}")

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        k = max(3, int(params.gauss_kernel) | 1)
        blurred = cv2.GaussianBlur(gray, (k, k), 0)

        edges = cv2.Canny(blurred, int(params.low_threshold), int(params.high_threshold))

        # Сливаем две стороны одного штриха в одну сплошную полосу: dilate утолщает
        # края Canny так, что параллельные грани одного штриха слипаются в одну фигуру.
        # Затем erode на ту же величину возвращает толщину к исходной — контур пойдёт
        # почти по реальной границе, без смещения наружу.
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        merged = cv2.dilate(edges, kernel, iterations=2)
        merged = cv2.erode(merged, kernel, iterations=2)

        # Берём все контуры с иерархией: внешние + дыры. Затем фильтруем дыры-«двойники»
        # (когда дыра занимает почти всю площадь родителя — это просто внутренний край
        # того же утолщённого штриха, а не настоящее отверстие в детали).
        contours, hierarchy = cv2.findContours(merged, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)

        # Сначала классифицируем каждый контур: круг или многоугольник.
        circles_fit: list[Circle | None] = [_fit_circle(c) for c in contours]

        # Затем фильтруем «двойников» (внешний/внутренний край одного штриха).
        # Если из пары двойников хотя бы один распознан как Circle — оставляем
        # именно его (он точнее представляет геометрию отверстия).
        keep_mask = [True] * len(contours)
        if hierarchy is not None:
            for i, cnt in enumerate(contours):
                parent = int(hierarchy[0][i][3])
                if parent < 0:
                    continue
                px, py, pw, ph = cv2.boundingRect(contours[parent])
                hx, hy, hw, hh = cv2.boundingRect(cnt)
                if pw == 0 or ph == 0:
                    continue
                if (hw / pw) <= 0.6 or (hh / ph) <= 0.6:
                    continue
                # Это пара двойников. Выбираем «лучшего».
                child_is_circle = circles_fit[i] is not None
                parent_is_circle = circles_fit[parent] is not None
                if child_is_circle and not parent_is_circle:
                    keep_mask[parent] = False
                elif parent_is_circle and not child_is_circle:
                    keep_mask[i] = False
                elif child_is_circle and parent_is_circle:
                    # Оба круги — оставляем внутренний (ближе к настоящей границе).
                    keep_mask[parent] = False
                else:
                    # Оба многоугольники — оставляем внешний (как раньше).
                    keep_mask[i] = False

        eps = max(0.1, float(params.dp_epsilon))
        result: list[Polyline | Circle] = []
        for i, contour in enumerate(contours):
            if not keep_mask[i]:
                continue

            if circles_fit[i] is not None:
                result.append(circles_fit[i])
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


def _fit_circle(contour) -> Circle | None:
    """Если контур близок к окружности, возвращает её. Иначе None.

    Сначала отсеивает по circularity (4π·area / perimeter²), затем проверяет,
    что все точки исходного контура лежат близко к минимальной описанной
    окружности (это отсекает правильные многоугольники, у которых circularity
    тоже высокая, но точки на рёбрах ближе к центру).
    """
    area = float(cv2.contourArea(contour))
    perim = float(cv2.arcLength(contour, closed=True))
    if perim <= 0 or area <= 0:
        return None
    circularity = 4.0 * np.pi * area / (perim * perim)
    if circularity < 0.78:
        return None

    (cx, cy), r = cv2.minEnclosingCircle(contour)
    if r < 3:
        return None

    # Точное различение круга и правильного многоугольника: считаем
    # относительный разброс расстояний точек контура от его центра.
    # У круга std/r ≈ 0.005–0.02, у шестиугольника ≈ 0.04–0.05.
    pts = contour.reshape(-1, 2).astype(np.float64)
    dists = np.linalg.norm(pts - np.array([cx, cy]), axis=1)
    std_rel = float(dists.std()) / r
    if std_rel < 0.035:
        return Circle(cx=float(cx), cy=float(cy), radius=float(r))
    return None
