"""Выделение контуров детали с растрового изображения.

Конвейер обработки:
    1. Загрузка изображения и перевод в полутоновое.
    2. Гауссово сглаживание для подавления шума.
    3. Алгоритм Canny — получение бинарной карты краёв.
    4. Морфологическое замыкание (dilate → erode) — устранение
       «двойного контура» вдоль каждого штриха.
    5. Поиск контуров методом cv2.findContours с иерархией RETR_CCOMP.
    6. Классификация каждого контура: окружность, дуга или произвольная
       ломаная. Распознавание окружностей и дуг основано на анализе
       расстояний точек контура от центра и углового покрытия.
    7. Фильтрация «двойников» — пар контуров, соответствующих внешнему
       и внутреннему краю одного и того же утолщённого штриха.
    8. Аппроксимация оставшихся контуров методом Дугласа–Пёкера.
"""
from __future__ import annotations

import math
from pathlib import Path

import cv2
import numpy as np

from core.models import Arc, CannyParams, Circle, Polyline


class ContourDetector:
    """Выделение контуров через Canny с последующей классификацией примитивов.

    Контуры, близкие к полной окружности, возвращаются как Circle;
    контуры, точки которых хорошо ложатся на дугу окружности (но не на
    полную) — как Arc; всё остальное — как Polyline (ломаные).
    """

    def detect(self, image_path: Path, params: CannyParams) -> list[Polyline | Circle | Arc]:
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

        # Шаг 7. Классификация каждого найденного контура.
        # Сначала пробуем как полную окружность; если не подошло —
        # пробуем как дугу. Если и дуга не подошла — позже обработаем
        # как полилинию через аппроксимацию Дугласа–Пёкера.
        # Результаты классификации сохраняем заранее, чтобы при фильтрации
        # двойников принимать решения с учётом типа примитива.
        circles_fit: list[Circle | None] = [_fit_circle(c) for c in contours]
        arcs_fit: list[Arc | None] = [
            None if circles_fit[i] is not None else _fit_arc(c)
            for i, c in enumerate(contours)
        ]

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
                # Окружности и дуги считаем «качественными» примитивами —
                # они несут больше CAD-семантики, чем ломаная.
                child_quality = circles_fit[i] is not None or arcs_fit[i] is not None
                parent_quality = circles_fit[parent] is not None or arcs_fit[parent] is not None
                if child_quality and not parent_quality:
                    # Дочерний — окружность/дуга, родитель — ломаная: оставляем дочерний.
                    keep_mask[parent] = False
                elif parent_quality and not child_quality:
                    keep_mask[i] = False
                elif child_quality and parent_quality:
                    # Оба — окружности/дуги: оставляем внутренний (он ближе
                    # к реальной границе после морфологии).
                    keep_mask[parent] = False
                else:
                    # Оба многоугольники — оставляем внешний контур.
                    keep_mask[i] = False

        # Шаг 9. Формирование итогового списка примитивов.
        # Приоритет: окружности → дуги целиком → ломаные (после аппроксимации).
        eps = max(0.1, float(params.dp_epsilon))
        result: list[Polyline | Circle | Arc] = []
        for i, contour in enumerate(contours):
            if not keep_mask[i]:
                continue

            if circles_fit[i] is not None:
                result.append(circles_fit[i])
                continue

            if arcs_fit[i] is not None:
                result.append(arcs_fit[i])
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


def _lsq_circle(pts: np.ndarray) -> tuple[float, float, float] | None:
    """Робастный фит окружности по точкам.

    Сначала алгебраический LSQ (быстрый, но смещён к хорде для дуг),
    затем 5 итераций геометрического уточнения по Гауссу–Ньютону:
    минимизируется истинное геометрическое расстояние точек от
    окружности (sqrt(Σ((dist−R)²) → min).

    Возвращает (cx, cy, R) или None, если фит не сошёлся.
    """
    if len(pts) < 3:
        return None

    # 1) Алгебраический начальный фит. Уравнение x²+y² = D·x+E·y+F,
    # где D = 2·cx, E = 2·cy, F = R² − cx² − cy².
    x = pts[:, 0]
    y = pts[:, 1]
    A = np.column_stack([x, y, np.ones_like(x)])
    b = x * x + y * y
    try:
        sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    except np.linalg.LinAlgError:
        return None
    cx = sol[0] / 2.0
    cy = sol[1] / 2.0
    r_sq = sol[2] + cx * cx + cy * cy
    if r_sq <= 0:
        return None
    r = math.sqrt(r_sq)

    # 2) Геометрическое уточнение методом Гаусса–Ньютона.
    # Остаток для точки i: f_i(cx, cy, R) = dist_i − R, где
    # dist_i = √((x_i−cx)² + (y_i−cy)²). Минимизируется ½·Σ f_i².
    # Якобиан строки i: J_i = [∂f_i/∂cx, ∂f_i/∂cy, ∂f_i/∂R] = [−ux, −uy, −1],
    # где ux = (x_i−cx)/dist_i, uy = (y_i−cy)/dist_i — единичный радиальный
    # вектор от центра к точке.
    # Шаг Гаусса–Ньютона: Δ = (JᵀJ)⁻¹ · (−Jᵀf). Раскрывая знаки получаем
    # положительные суммы — это даёт численно устойчивую систему.
    for _ in range(20):
        dx = x - cx
        dy = y - cy
        dist = np.hypot(dx, dy)
        # Избегаем деления на ноль (если какая-то точка совпала с центром).
        safe = np.maximum(dist, 1e-9)
        ux = dx / safe
        uy = dy / safe
        residual = dist - r

        sum_ux = float(ux.sum())
        sum_uy = float(uy.sum())
        JtJ = np.array([
            [float((ux * ux).sum()), float((ux * uy).sum()), sum_ux],
            [float((ux * uy).sum()), float((uy * uy).sum()), sum_uy],
            [sum_ux,                  sum_uy,                 float(len(pts))],
        ])
        # Правая часть = −Jᵀf. С учётом J_i = [−ux, −uy, −1]:
        # (Jᵀf)_0 = Σ(−ux)·f = −Σ ux·f  ⇒  −(Jᵀf)_0 = Σ ux·f.
        rhs = np.array([
            float((ux * residual).sum()),
            float((uy * residual).sum()),
            float(residual.sum()),
        ])
        try:
            step = np.linalg.solve(JtJ, rhs)
        except np.linalg.LinAlgError:
            break
        cx += float(step[0])
        cy += float(step[1])
        r += float(step[2])
        if r <= 0:
            return None
        # Сходимость — если все компоненты шага очень малы.
        if abs(step[0]) + abs(step[1]) + abs(step[2]) < 1e-6:
            break

    return float(cx), float(cy), float(r)


def _fit_arc(contour) -> Arc | None:
    """Пытается распознать контур как дугу окружности.

    Алгоритм:
        1. LSQ-фит окружности по всем точкам контура.
        2. Отброс заведомо неподходящих случаев (слишком малый/большой
           радиус, точки слабо ложатся на окружность).
        3. Анализ углового покрытия: ищем самый большой пропуск (gap)
           в углах atan2 относительно найденного центра. Если пропуск
           больше ~18° (т. е. дуга покрывает заметно меньше 360°),
           но при этом сама дуга шире ~63° — это и есть дуга.

    Возвращает Arc с end_angle > start_angle (гарантия положительного
    направления обхода) или None, если контур не дуга.
    """
    pts = contour.reshape(-1, 2).astype(np.float64)
    # Слишком мало точек — фит ненадёжен.
    if len(pts) < 20:
        return None

    fit = _lsq_circle(pts)
    if fit is None:
        return None
    cx, cy, r = fit

    # Радиус должен быть осмысленным. Отбрасываем «дуги-километры», когда
    # контур — это длинная тонкая полоса (например, прямая линия), и LSQ
    # пытается приблизить её огромной окружностью.
    if r < 5.0:
        return None
    x, y, w, h = cv2.boundingRect(contour)
    bbox_diag = math.hypot(w, h)
    if r > 3.0 * bbox_diag:
        return None

    # Точки контура должны быть приблизительно равноудалены от центра.
    # Поскольку контур — это перимент тонкой полосы вокруг дуги, точки
    # лежат на двух близких радиусах (внешнем и внутреннем) плюс концы;
    # допуск std/r поэтому шире, чем для полной окружности.
    dists = np.linalg.norm(pts - np.array([cx, cy]), axis=1)
    rel_std = float(dists.std()) / r
    if rel_std > 0.12:
        return None

    # Угловое покрытие: считаем углы точек относительно центра, ищем
    # самый большой «пропуск» в покрытии — это и есть отсутствующая
    # часть окружности (та самая, что отличает дугу от полного круга).
    angles = np.arctan2(pts[:, 1] - cy, pts[:, 0] - cx)
    a_sorted = np.sort(angles)
    gaps = np.diff(a_sorted)
    # «Замыкающий» пропуск через ±π:
    wrap_gap = (a_sorted[0] + 2.0 * math.pi) - a_sorted[-1]
    interior_max = float(gaps.max()) if len(gaps) > 0 else 0.0
    max_gap = max(interior_max, wrap_gap)
    coverage = 2.0 * math.pi - max_gap

    # Почти полное покрытие — это окружность, её обрабатывает _fit_circle.
    if coverage > 1.9 * math.pi:        # больше ~342°
        return None
    # Слишком узкая дуга — скорее всего шум или малозначимая деталь.
    if coverage < 0.35 * math.pi:       # меньше ~63°
        return None

    # Определяем start/end на основе того, ГДЕ именно расположен gap.
    # Если самый большой пропуск — замыкающий (через ±π), то дуга
    # непрерывна в массиве отсортированных углов: от a_sorted[0] до a_sorted[-1].
    # Иначе пропуск — где-то внутри; тогда дуга проходит через ±π.
    if wrap_gap >= interior_max:
        start = float(a_sorted[0])
        end = float(a_sorted[-1])
    else:
        gap_idx = int(np.argmax(gaps))
        start = float(a_sorted[gap_idx + 1])
        # К концу прибавляем 2π, чтобы end > start (дуга «разворачивается»
        # через ±π — без сдвига end оказался бы численно меньше start).
        end = float(a_sorted[gap_idx]) + 2.0 * math.pi

    # Радиус берём как медиану расстояний — это устойчиво к выбросам
    # на концах полосы и точнее центральной линии дуги, чем LSQ-радиус.
    median_r = float(np.median(dists))

    return Arc(
        cx=float(cx),
        cy=float(cy),
        radius=median_r,
        start_angle=start,
        end_angle=end,
    )
