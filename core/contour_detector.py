"""Выделение контуров детали с растрового изображения.

Конвейер обработки:
    1. Загрузка изображения и перевод в полутоновое.
    2. Гауссово сглаживание для подавления шума.
    3. Алгоритм Canny — получение бинарной карты краёв.
    4. Морфологическое замыкание (dilate → erode) — устранение
       «двойного контура» вдоль каждого штриха.
    5. Поиск контуров методом cv2.findContours с иерархией RETR_CCOMP.
    6. Классификация каждого контура: окружность или произвольная ломаная
       (по критериям circularity и относительного разброса расстояний
       точек от центра).
    7. Фильтрация «двойников» — пар контуров, соответствующих внешнему
       и внутреннему краю одного и того же утолщённого штриха.
    8. Аппроксимация оставшихся контуров методом Дугласа–Пёкера.
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from core.models import CannyParams, Circle, Polyline


class ContourDetector:
    """Выделение контуров через Canny с последующей классификацией примитивов.

    Контуры, близкие к окружности, возвращаются как объекты Circle;
    все остальные — как Polyline (ломаные).
    """

    def detect(self, image_path: Path, params: CannyParams) -> list[Polyline | Circle]:
        """Полный конвейер выделения контуров из файла изображения.

        Возвращает смешанный список геометрических примитивов: окружности
        и ломаные, готовые к передаче в генератор эскиза.
        """
        # Шаг 1. Загрузка изображения (OpenCV читает как BGR).
        img = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError(f"Не удалось прочитать изображение: {image_path}")

        # Шаг 2. Перевод в полутоновое (Canny работает с одноканальным).
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Шаг 3. Гауссово сглаживание. Размер ядра должен быть нечётным,
        # поэтому принудительно выставляем младший бит в 1 операцией `| 1`.
        k = max(3, int(params.gauss_kernel) | 1)
        blurred = cv2.GaussianBlur(gray, (k, k), 0)

        # Шаг 4. Алгоритм Кэнни: вычисление градиентов, подавление
        # немаксимумов и двойная пороговая фильтрация.
        edges = cv2.Canny(blurred, int(params.low_threshold), int(params.high_threshold))

        # Шаг 5. Морфологическое замыкание: сначала dilate утолщает каждый
        # край Canny так, что параллельные грани одного штриха слипаются
        # в одну сплошную фигуру; затем erode на ту же величину
        # возвращает толщину к исходной. Итог — контур проходит почти
        # по реальной границе детали, без смещения наружу.
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        merged = cv2.dilate(edges, kernel, iterations=2)
        merged = cv2.erode(merged, kernel, iterations=2)

        # Шаг 6. Поиск контуров с иерархией (внешние + дыры).
        # RETR_CCOMP возвращает двухуровневую иерархию: верхний уровень
        # — внешние контуры, нижний — дыры (отверстия) внутри них.
        contours, hierarchy = cv2.findContours(merged, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)

        # Шаг 7. Классификация каждого найденного контура: круг или нет.
        # Сохраняем результат заранее, чтобы при фильтрации двойников
        # принимать решения с учётом типа примитива.
        circles_fit: list[Circle | None] = [_fit_circle(c) for c in contours]

        # Шаг 8. Фильтрация «двойников» — пар (внешний + внутренний край
        # одного утолщённого штриха). Признак двойника: дочерний контур
        # (дыра) занимает почти всю площадь родителя (>60% по обеим осям).
        keep_mask = [True] * len(contours)
        if hierarchy is not None:
            for i, cnt in enumerate(contours):
                # Индекс родителя в иерархии: hierarchy[0][i] = [next, prev, child, parent]
                parent = int(hierarchy[0][i][3])
                if parent < 0:
                    # Контур верхнего уровня — двойников быть не может.
                    continue
                px, py, pw, ph = cv2.boundingRect(contours[parent])
                hx, hy, hw, hh = cv2.boundingRect(cnt)
                if pw == 0 or ph == 0:
                    continue
                # Если дыра меньше 60% размера родителя — это настоящее
                # отверстие в детали, оставляем оба контура.
                if (hw / pw) <= 0.6 or (hh / ph) <= 0.6:
                    continue
                # Иначе это пара двойников: оставляем «лучший» из двух.
                child_is_circle = circles_fit[i] is not None
                parent_is_circle = circles_fit[parent] is not None
                if child_is_circle and not parent_is_circle:
                    # Окружность точнее ломаной — оставляем дочерний.
                    keep_mask[parent] = False
                elif parent_is_circle and not child_is_circle:
                    keep_mask[i] = False
                elif child_is_circle and parent_is_circle:
                    # Оба распознаны как окружности — оставляем внутренний
                    # (он ближе к реальной границе после морфологии).
                    keep_mask[parent] = False
                else:
                    # Оба многоугольники — оставляем внешний контур.
                    keep_mask[i] = False

        # Шаг 9. Формирование итогового списка примитивов.
        # Окружности — как есть; ломаные — после аппроксимации Дугласа–Пёкера.
        eps = max(0.1, float(params.dp_epsilon))
        result: list[Polyline | Circle] = []
        for i, contour in enumerate(contours):
            if not keep_mask[i]:
                continue

            if circles_fit[i] is not None:
                result.append(circles_fit[i])
                continue

            # Аппроксимация Дугласа–Пёкера: уменьшение количества точек
            # ломаной с сохранением общей формы (допуск eps в пикселях).
            approx = cv2.approxPolyDP(contour, eps, closed=True)
            pts: list[tuple[float, float]] = [
                (float(p[0][0]), float(p[0][1])) for p in approx
            ]
            # Отбрасываем вырожденные контуры (точка, отрезок).
            if len(pts) < 3:
                continue
            # Замыкаем ломаную, если первая и последняя точки не совпадают.
            if pts[0] != pts[-1]:
                pts.append(pts[0])
            result.append(Polyline(points=pts))

        return result


def _fit_circle(contour) -> Circle | None:
    """Определяет, можно ли считать контур окружностью.

    Используется двухступенчатый критерий:

    1. Циркулярность 4π·S / P² должна быть близка к 1 (порог 0.78).
       У идеального круга — ровно 1, у квадрата — около 0.785,
       у шестиугольника — около 0.907. Один этот порог не отсеивает
       правильные многоугольники, поэтому добавляется второй шаг.
    2. Относительный разброс расстояний точек контура от центра
       (σ / R) должен быть очень малым (< 0.035). У окружности все
       точки лежат на радиусе R и σ/R ≈ 0.005–0.02; у правильного
       шестиугольника точки на рёбрах ближе к центру, σ/R ≈ 0.04–0.05.

    Возвращает Circle, если контур признан окружностью, иначе None.
    """
    area = float(cv2.contourArea(contour))
    perim = float(cv2.arcLength(contour, closed=True))
    if perim <= 0 or area <= 0:
        return None

    # Шаг 1. Проверка циркулярности.
    circularity = 4.0 * np.pi * area / (perim * perim)
    if circularity < 0.78:
        return None

    # Минимальная описанная окружность даёт центр и радиус.
    (cx, cy), r = cv2.minEnclosingCircle(contour)
    if r < 3:
        # Слишком малые окружности игнорируем — это, как правило, шум.
        return None

    # Шаг 2. Точное различение круга и правильного многоугольника.
    pts = contour.reshape(-1, 2).astype(np.float64)
    dists = np.linalg.norm(pts - np.array([cx, cy]), axis=1)
    std_rel = float(dists.std()) / r
    if std_rel < 0.035:
        return Circle(cx=float(cx), cy=float(cy), radius=float(r))
    return None
