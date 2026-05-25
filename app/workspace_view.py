"""Рабочая область приложения (центральный виджет).

WorkspaceView построен на QGraphicsView/QGraphicsScene и отвечает за:

    * отображение исходного растрового изображения;
    * масштабирование (зум колесом, fit-to-view) и панорамирование;
    * наложение слоёв «контуры» (красные) и «эскиз» (синие);
    * режим интерактивной калибровки: пользователь кликает две точки
      на изображении, виджет рисует маркеры и линию, эмиттит сигналы.

Все примитивы хранятся в пиксельных координатах исходного изображения.
"""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QPointF, Qt, pyqtSignal
from PyQt6.QtCore import QRectF
from PyQt6.QtGui import QColor, QCursor, QImage, QPainter, QPainterPath, QPen, QPixmap, QWheelEvent
from PyQt6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsLineItem,
    QGraphicsPathItem,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsView,
)

from core.models import Circle, Polyline

class WorkspaceView(QGraphicsView):
    """Рабочая область: изображение + слои контуров, эскиза и калибровки."""

    # Уведомления для статус-бара главного окна.
    zoomChanged = pyqtSignal(float)
    mouseScenePosChanged = pyqtSignal(QPointF)

    # Сигналы режима калибровки: первая точка задана / обе заданы / отменено.
    # Параметры — координаты точек в пикселях исходного изображения.
    calibrationPoint1Set = pyqtSignal(int, int)
    calibrationCompleted = pyqtSignal(int, int, int, int)
    calibrationCancelled = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        # Сглаживание для плавных контуров и масштабирования изображения.
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing
            | QPainter.RenderHint.SmoothPixmapTransform
        )
        # При зуме якорь — позиция курсора (удобно для приближения детали).
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        # Перетаскивание «рукой» по умолчанию (отключается в режиме калибровки).
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        # Полная перерисовка viewport'а — избавляет от артефактов при зуме.
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        # Включаем mouseMoveEvent даже без зажатой кнопки (для статуса).
        self.setMouseTracking(True)

        # Сцена с тёмным фоном — единый стиль приложения.
        self._scene = QGraphicsScene(self)
        self._scene.setBackgroundBrush(QColor("#16181c"))
        self.setScene(self._scene)
        self.setFrameShape(self.Shape.NoFrame)
        self.setBackgroundBrush(QColor("#16181c"))

        # Хранение текущих графических элементов сцены —
        # списки нужны, чтобы потом аккуратно удалить старые перед перерисовкой.
        self._image_item: QGraphicsPixmapItem | None = None
        self._contour_items: list[QGraphicsItem] = []
        self._sketch_items: list[QGraphicsItem] = []
        self._zoom = 1.0

        # Состояние режима интерактивной калибровки.
        self._calibration_mode: bool = False
        self._calib_point1: tuple[int, int] | None = None  # координаты первой точки
        self._calib_items: list[QGraphicsItem] = []        # маркеры и линия на сцене

    def clear_all(self) -> None:
        self._scene.clear()
        self._image_item = None
        self._contour_items.clear()
        self._sketch_items.clear()
        self._calib_items.clear()
        self._calib_point1 = None
        self._zoom = 1.0
        self.zoomChanged.emit(self._zoom)

    # --- Калибровка ---

    def is_calibration_mode(self) -> bool:
        return self._calibration_mode

    def set_calibration_mode(self, enabled: bool) -> None:
        """Включает/выключает режим калибровки.

        В режиме калибровки:
            - отключается панорамирование (иначе клик может «уплыть»);
            - курсор меняется на крест;
            - левый клик регистрируется как опорная точка.
        """
        if enabled and self._image_item is None:
            return
        self._calibration_mode = enabled
        self._calib_point1 = None
        # Очищаем все артефакты предыдущей калибровки (точки, линию, подпись).
        for item in self._calib_items:
            self._scene.removeItem(item)
        self._calib_items.clear()
        if enabled:
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.viewport().setCursor(QCursor(Qt.CursorShape.CrossCursor))
        else:
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            self.viewport().unsetCursor()

    def _add_calib_marker(self, x: float, y: float) -> None:
        """Рисует красный круглый маркер в указанной точке сцены."""
        pen = QPen(QColor(220, 50, 47))
        pen.setWidth(2)
        # cosmetic=True — толщина линии не меняется при зуме (всегда 2 пикселя экрана).
        pen.setCosmetic(True)
        r = 6.0  # радиус маркера в координатах сцены (= пикселях изображения)
        dot = QGraphicsEllipseItem(x - r, y - r, r * 2, r * 2)
        dot.setPen(pen)
        # Полупрозрачная заливка (alpha=90), чтобы не закрывать саму точку детали.
        dot.setBrush(QColor(220, 50, 47, 90))
        # Высокий Z-уровень: маркер всегда поверх контуров и эскиза.
        dot.setZValue(30)
        self._scene.addItem(dot)
        self._calib_items.append(dot)

    def _add_calib_line(self, x1: float, y1: float, x2: float, y2: float) -> None:
        """Рисует пунктирную линию между двумя опорными точками и подпись с расстоянием."""
        pen = QPen(QColor(220, 50, 47))
        pen.setWidth(2)
        pen.setStyle(Qt.PenStyle.DashLine)
        pen.setCosmetic(True)
        line = QGraphicsLineItem(x1, y1, x2, y2)
        line.setPen(pen)
        line.setZValue(30)
        self._scene.addItem(line)
        self._calib_items.append(line)

        # Текстовая подпись с расстоянием в пикселях — для наглядности.
        import math
        dist = math.hypot(x2 - x1, y2 - y1)
        label = QGraphicsSimpleTextItem(f"{dist:.1f} пикс.")
        label.setBrush(QColor(220, 50, 47))
        # Сдвиг подписи относительно середины отрезка, чтобы не закрывала саму линию.
        label.setPos((x1 + x2) / 2 + 8, (y1 + y2) / 2 + 8)
        label.setZValue(31)
        self._scene.addItem(label)
        self._calib_items.append(label)

    def load_image(self, path: Path) -> None:
        image = QImage(str(path))
        if image.isNull():
            raise ValueError("Файл не является корректным изображением или не поддерживается.")
        self.set_image(image)

    def set_image(self, image: QImage) -> None:
        """Загружает новое изображение на сцену и подгоняет под окно."""
        self.clear_all()
        pix = QPixmap.fromImage(image)
        self._image_item = self._scene.addPixmap(pix)
        # Z=0 — самый нижний слой; над ним рисуются контуры и эскиз.
        self._image_item.setZValue(0)

        # Размер сцены = размеру изображения (для корректного fit-to-view).
        self._scene.setSceneRect(QRectF(pix.rect()))
        self.fit_to_view()

    def image_size(self) -> tuple[int, int]:
        if self._image_item is None:
            return (0, 0)
        rect = self._image_item.pixmap().rect()
        return (int(rect.width()), int(rect.height()))

    def zoom_factor(self) -> float:
        return float(self._zoom)

    def fit_to_view(self) -> None:
        if self._image_item is None:
            return
        self.resetTransform()
        self._zoom = 1.0
        self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self.zoomChanged.emit(self._zoom)

    def zoom_in(self) -> None:
        self._apply_zoom(1.15)

    def zoom_out(self) -> None:
        self._apply_zoom(1 / 1.15)

    def zoom_100(self) -> None:
        if self._image_item is None:
            return
        self.resetTransform()
        self._zoom = 1.0
        self.zoomChanged.emit(self._zoom)

    def _apply_zoom(self, factor: float) -> None:
        """Применяет коэффициент зума с ограничением диапазона 0.05x–50x."""
        if self._image_item is None:
            return
        new_zoom = self._zoom * factor
        # Защита от «уезжания» изображения в бесконечно малое/большое.
        if new_zoom < 0.05 or new_zoom > 50.0:
            return
        self._zoom = new_zoom
        self.scale(factor, factor)
        self.zoomChanged.emit(self._zoom)

    def wheelEvent(self, event: QWheelEvent) -> None:
        """Зум колесом мыши без зажатого Ctrl — привычное поведение CAD."""
        if event.angleDelta().y() == 0:
            return
        if event.angleDelta().y() > 0:
            self.zoom_in()
        else:
            self.zoom_out()
        event.accept()

    def mouseMoveEvent(self, event) -> None:  # type: ignore[override]
        pos = self.mapToScene(event.pos())
        self.mouseScenePosChanged.emit(pos)
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        """Обработка кликов в режиме калибровки.

        Левый клик ставит маркер; первый клик — запоминаем точку,
        второй — рисуем линию между ними и эмиттим calibrationCompleted.
        """
        # Не калибруем или не левая кнопка — стандартное поведение (drag).
        if not self._calibration_mode or event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return

        # Перевод координат вьюпорта в координаты сцены (пиксели изображения).
        scene_pos = self.mapToScene(event.pos())
        x, y = int(round(scene_pos.x())), int(round(scene_pos.y()))

        # Клик вне изображения игнорируем — иначе калибровка получит
        # бессмысленные отрицательные координаты или координаты вне детали.
        if self._image_item is not None:
            rect = self._image_item.pixmap().rect()
            if not (0 <= x < rect.width() and 0 <= y < rect.height()):
                return

        if self._calib_point1 is None:
            # Первый клик — запоминаем точку, рисуем маркер, уведомляем.
            self._calib_point1 = (x, y)
            self._add_calib_marker(x, y)
            self.calibrationPoint1Set.emit(x, y)
        else:
            # Второй клик — завершаем калибровку.
            x1, y1 = self._calib_point1
            self._add_calib_marker(x, y)
            self._add_calib_line(x1, y1, x, y)
            self.calibrationCompleted.emit(x1, y1, x, y)
        event.accept()

    def generate_demo_contours(self) -> list[Polyline]:
        """Один прямоугольный контур по границе изображения."""
        if self._image_item is None:
            return []
        rect = self._image_item.pixmap().rect()
        w, h = float(rect.width()), float(rect.height())
        pad = 10.0
        return [
            Polyline(
                points=[
                    (pad, pad),
                    (w - pad, pad),
                    (w - pad, h - pad),
                    (pad, h - pad),
                    (pad, pad),
                ]
            )
        ]

    def show_contours(self, contours: list[Polyline]) -> None:
        """Отображает слой контуров (красный) поверх изображения."""
        self._draw_polylines(
            target_list=self._contour_items,
            polylines=contours,
            color=QColor(220, 50, 47),  # красный
            width=2,
            z=10,  # выше изображения (z=0), ниже эскиза (z=20)
        )

    def show_sketch(self, sketch_entities: list[Polyline]) -> None:
        """Отображает слой эскиза (синий) поверх контуров."""
        self._draw_polylines(
            target_list=self._sketch_items,
            polylines=sketch_entities,
            color=QColor(38, 139, 210),  # синий
            width=2,
            z=20,
        )

    def _draw_polylines(
        self,
        target_list: list[QGraphicsItem],
        polylines: list[Polyline | Circle],
        color: QColor,
        width: int,
        z: int,
    ) -> None:
        """Перерисовывает слой геометрии заданным цветом.

        Сначала удаляет старые элементы слоя, затем добавляет новые.
        Окружности рисуются как QGraphicsEllipseItem (нативные круги),
        ломаные — как QGraphicsPathItem через QPainterPath.
        """
        # Удаляем старые элементы этого слоя — иначе они накопятся при повторных вызовах.
        for item in target_list:
            self._scene.removeItem(item)
        target_list.clear()

        if not polylines:
            return

        pen = QPen(color)
        pen.setWidth(width)
        # cosmetic=True — толщина линии в пикселях экрана, а не сцены.
        # Иначе при зуме линии становились бы непропорционально толстыми.
        pen.setCosmetic(True)

        for ent in polylines:
            if isinstance(ent, Circle):
                # Окружность как нативный примитив — рисуется идеально гладкой.
                item: QGraphicsItem = QGraphicsEllipseItem(
                    ent.cx - ent.radius, ent.cy - ent.radius,
                    ent.radius * 2, ent.radius * 2,
                )
                item.setPen(pen)
            else:
                # Ломаная: строим путь по точкам последовательно.
                if len(ent.points) < 2:
                    continue
                path = QPainterPath()
                x0, y0 = ent.points[0]
                path.moveTo(x0, y0)
                for x, y in ent.points[1:]:
                    path.lineTo(x, y)
                item = QGraphicsPathItem(path)
                item.setPen(pen)

            item.setZValue(z)
            self._scene.addItem(item)
            target_list.append(item)

