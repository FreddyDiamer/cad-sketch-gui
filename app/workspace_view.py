from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QPointF, Qt, pyqtSignal
from PyQt6.QtCore import QRectF
from PyQt6.QtGui import QColor, QImage, QPainter, QPainterPath, QPen, QPixmap, QWheelEvent
from PyQt6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsPathItem,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsView,
)

from core.models import Circle, Polyline

class WorkspaceView(QGraphicsView):
    """Рабочая область: просмотр изображения и примитивные оверлеи (контуры)."""

    zoomChanged = pyqtSignal(float)
    mouseScenePosChanged = pyqtSignal(QPointF)

    def __init__(self) -> None:
        super().__init__()
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing
            | QPainter.RenderHint.SmoothPixmapTransform
        )
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.setMouseTracking(True)

        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)

        self._image_item: QGraphicsPixmapItem | None = None
        self._contour_items: list[QGraphicsItem] = []
        self._sketch_items: list[QGraphicsItem] = []
        self._zoom = 1.0

    def clear_all(self) -> None:
        self._scene.clear()
        self._image_item = None
        self._contour_items.clear()
        self._sketch_items.clear()
        self._zoom = 1.0
        self.zoomChanged.emit(self._zoom)

    def load_image(self, path: Path) -> None:
        image = QImage(str(path))
        if image.isNull():
            raise ValueError("Файл не является корректным изображением или не поддерживается.")
        self.set_image(image)

    def set_image(self, image: QImage) -> None:
        self.clear_all()
        pix = QPixmap.fromImage(image)
        self._image_item = self._scene.addPixmap(pix)
        self._image_item.setZValue(0)

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
        if self._image_item is None:
            return
        new_zoom = self._zoom * factor
        if new_zoom < 0.05 or new_zoom > 50.0:
            return
        self._zoom = new_zoom
        self.scale(factor, factor)
        self.zoomChanged.emit(self._zoom)

    def wheelEvent(self, event: QWheelEvent) -> None:
        if event.angleDelta().y() == 0:
            return
        # Удобный UX: зум колесом мыши, Ctrl не требуется.
        if event.angleDelta().y() > 0:
            self.zoom_in()
        else:
            self.zoom_out()
        event.accept()

    def mouseMoveEvent(self, event) -> None:  # type: ignore[override]
        pos = self.mapToScene(event.pos())
        self.mouseScenePosChanged.emit(pos)
        super().mouseMoveEvent(event)

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
        self._draw_polylines(
            target_list=self._contour_items,
            polylines=contours,
            color=QColor(220, 50, 47),  # красный
            width=2,
            z=10,
        )

    def show_sketch(self, sketch_entities: list[Polyline]) -> None:
        """Показ эскиза отдельным слоем."""
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
        for item in target_list:
            self._scene.removeItem(item)
        target_list.clear()

        if not polylines:
            return

        pen = QPen(color)
        pen.setWidth(width)
        pen.setCosmetic(True)  # толщина не меняется при зуме

        for ent in polylines:
            if isinstance(ent, Circle):
                item: QGraphicsItem = QGraphicsEllipseItem(
                    ent.cx - ent.radius, ent.cy - ent.radius,
                    ent.radius * 2, ent.radius * 2,
                )
                item.setPen(pen)
            else:
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

