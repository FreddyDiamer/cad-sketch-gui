from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from core.models import CannyParams, Circle, Polyline, ProjectState


_STATE_PENDING = "pending"
_STATE_ACTIVE = "active"
_STATE_DONE = "done"


def _set_primary(btn: QPushButton, primary: bool) -> None:
    """Переключает property primary и заставляет стиль перерисоваться."""
    btn.setProperty("primary", "true" if primary else "false")
    btn.style().unpolish(btn)
    btn.style().polish(btn)
    btn.update()


def _repolish(w: QWidget) -> None:
    w.style().unpolish(w)
    w.style().polish(w)
    w.update()


class _StepCard(QFrame):
    """Карточка одного шага: бейдж, заголовок, value, контент."""

    def __init__(self, number: int, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("stepCard")
        self.setFrameShape(QFrame.Shape.NoFrame)
        self._number = number

        self._badge = QLabel(str(number))
        self._badge.setObjectName("stepBadge")
        self._badge.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._title = QLabel(title)
        self._title.setObjectName("stepTitle")

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(10)
        header.addWidget(self._badge)
        header.addWidget(self._title, 1)

        self._value_lbl = QLabel("")
        self._value_lbl.setObjectName("stepValue")
        self._value_lbl.setWordWrap(True)
        self._value_lbl.hide()

        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(0, 8, 0, 0)
        self._content_layout.setSpacing(8)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 12, 14, 12)
        outer.setSpacing(6)
        outer.addLayout(header)
        outer.addWidget(self._value_lbl)
        outer.addWidget(self._content)

        self.set_state(_STATE_PENDING)

    def set_state(self, state: str) -> None:
        self.setProperty("state", state)
        self._badge.setProperty("state", state)
        if state == _STATE_DONE:
            self._badge.setText("✓")
        else:
            self._badge.setText(str(self._number))
        _repolish(self)
        _repolish(self._badge)

    def set_value(self, text: str) -> None:
        if text:
            self._value_lbl.setText(text)
            self._value_lbl.show()
        else:
            self._value_lbl.hide()

    def content_layout(self) -> QVBoxLayout:
        return self._content_layout

    def show_content(self, visible: bool) -> None:
        self._content.setVisible(visible)


class StepPanel(QWidget):
    """Левая панель из 6 шагов: от создания проекта до экспорта DXF."""

    requestCreateProject = pyqtSignal()
    requestOpenProject = pyqtSignal()
    requestSaveProject = pyqtSignal()
    requestImportImage = pyqtSignal()
    requestStartCalibration = pyqtSignal()
    requestApplyCanny = pyqtSignal(CannyParams)
    requestBuildSketch = pyqtSignal()
    requestExportDxf = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumWidth(300)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)

        self._card1 = _StepCard(1, "Проект")
        self._card2 = _StepCard(2, "Изображение")
        self._card3 = _StepCard(3, "Калибровка")
        self._card4 = _StepCard(4, "Контуры")
        self._card5 = _StepCard(5, "Эскиз")
        self._card6 = _StepCard(6, "Экспорт DXF")

        self._build_card1()
        self._build_card2()
        self._build_card3()
        self._build_card4()
        self._build_card5()
        self._build_card6()

        self._cards: list[_StepCard] = [
            self._card1, self._card2, self._card3,
            self._card4, self._card5, self._card6,
        ]

        inner = QWidget()
        inner_layout = QVBoxLayout(inner)
        inner_layout.setContentsMargins(12, 12, 12, 12)
        inner_layout.setSpacing(10)
        for card in self._cards:
            inner_layout.addWidget(card)
        inner_layout.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidget(inner)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    # ---------- card builders ----------

    def _build_card1(self) -> None:
        layout = self._card1.content_layout()
        self._btn_create = QPushButton("Создать проект…")
        self._btn_open = QPushButton("Открыть проект…")
        self._btn_save = QPushButton("Сохранить")
        self._btn_create.clicked.connect(self.requestCreateProject)
        self._btn_open.clicked.connect(self.requestOpenProject)
        self._btn_save.clicked.connect(self.requestSaveProject)
        _set_primary(self._btn_create, True)
        layout.addWidget(self._btn_create)
        layout.addWidget(self._btn_open)
        layout.addWidget(self._btn_save)

    def _build_card2(self) -> None:
        layout = self._card2.content_layout()
        self._btn_import = QPushButton("Импортировать изображение…")
        self._btn_import.clicked.connect(self.requestImportImage)
        _set_primary(self._btn_import, True)
        layout.addWidget(self._btn_import)

    def _build_card3(self) -> None:
        layout = self._card3.content_layout()
        hint = QLabel(
            "Кликните две точки на изображении с известным расстоянием "
            "(например, концы линейки)."
        )
        hint.setObjectName("stepHint")
        hint.setWordWrap(True)
        self._btn_calibrate = QPushButton("Откалибровать…")
        self._btn_calibrate.clicked.connect(self.requestStartCalibration)
        _set_primary(self._btn_calibrate, True)
        layout.addWidget(hint)
        layout.addWidget(self._btn_calibrate)

    def _build_card4(self) -> None:
        layout = self._card4.content_layout()

        self._low_slider, self._low_spin = self._make_slider_spin(0, 255, 50)
        self._high_slider, self._high_spin = self._make_slider_spin(0, 255, 150)

        self._gauss = QSpinBox()
        self._gauss.setRange(3, 15)
        self._gauss.setSingleStep(2)
        self._gauss.setValue(5)
        self._gauss.setToolTip("Размер ядра Гаусса (нечётное). Больше — сильнее сглаживание шума.")

        self._eps = QDoubleSpinBox()
        self._eps.setRange(0.1, 50.0)
        self._eps.setSingleStep(0.1)
        self._eps.setDecimals(2)
        self._eps.setValue(2.0)
        self._eps.setToolTip(
            "Допуск аппроксимации Дугласа–Пекера в пикселях. "
            "Меньше = точнее форма (больше точек)."
        )

        layout.addLayout(self._row("Нижний порог", self._low_slider, self._low_spin))
        layout.addLayout(self._row("Верхний порог", self._high_slider, self._high_spin))
        layout.addLayout(self._row_pair("Размытие", self._gauss, "Сглаживание", self._eps))

        self._auto_check = QCheckBox("Авто-обновление")
        self._auto_check.setChecked(True)
        self._auto_check.setToolTip("Контуры пересчитываются автоматически при изменении параметров")
        layout.addWidget(self._auto_check)

        self._btn_apply = QPushButton("Применить")
        self._btn_apply.clicked.connect(self._emit_apply_canny)
        _set_primary(self._btn_apply, True)
        layout.addWidget(self._btn_apply)

        self._contours_info = QLabel("")
        self._contours_info.setObjectName("stepValue")
        self._contours_info.setWordWrap(True)
        self._contours_info.hide()
        layout.addWidget(self._contours_info)

        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(300)
        self._preview_timer.timeout.connect(self._emit_apply_canny)

        for w in (self._low_slider, self._high_slider, self._low_spin,
                  self._high_spin, self._gauss):
            w.valueChanged.connect(self._on_param_changed)
        self._eps.valueChanged.connect(self._on_param_changed)

    def _build_card5(self) -> None:
        layout = self._card5.content_layout()
        self._btn_sketch = QPushButton("Построить эскиз")
        self._btn_sketch.clicked.connect(self.requestBuildSketch)
        _set_primary(self._btn_sketch, True)
        layout.addWidget(self._btn_sketch)
        self._sketch_info = QLabel("")
        self._sketch_info.setObjectName("stepValue")
        self._sketch_info.hide()
        layout.addWidget(self._sketch_info)

    def _build_card6(self) -> None:
        layout = self._card6.content_layout()
        self._btn_export = QPushButton("Экспортировать DXF…")
        self._btn_export.clicked.connect(self.requestExportDxf)
        _set_primary(self._btn_export, True)
        layout.addWidget(self._btn_export)
        self._export_info = QLabel("")
        self._export_info.setObjectName("stepValue")
        self._export_info.setWordWrap(True)
        self._export_info.hide()
        layout.addWidget(self._export_info)

    # ---------- helpers ----------

    @staticmethod
    def _make_slider_spin(lo: int, hi: int, value: int) -> tuple[QSlider, QSpinBox]:
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(lo, hi)
        slider.setValue(value)
        spin = QSpinBox()
        spin.setRange(lo, hi)
        spin.setValue(value)
        spin.setMinimumWidth(60)
        slider.valueChanged.connect(spin.setValue)
        spin.valueChanged.connect(slider.setValue)
        return slider, spin

    @staticmethod
    def _row(label: str, slider: QSlider, spin: QSpinBox) -> QVBoxLayout:
        wrap = QVBoxLayout()
        wrap.setSpacing(2)
        lbl = QLabel(label)
        lbl.setStyleSheet("color: #8b949e; font-size: 11px;")
        h = QHBoxLayout()
        h.setSpacing(8)
        h.addWidget(slider, 1)
        spin.setMaximumWidth(64)
        h.addWidget(spin)
        wrap.addWidget(lbl)
        wrap.addLayout(h)
        return wrap

    @staticmethod
    def _row_pair(label1: str, w1: QWidget, label2: str, w2: QWidget) -> QHBoxLayout:
        h = QHBoxLayout()
        h.setSpacing(8)
        # колонка 1
        col1 = QVBoxLayout(); col1.setSpacing(2)
        lbl1 = QLabel(label1); lbl1.setStyleSheet("color: #8b949e; font-size: 11px;")
        col1.addWidget(lbl1); col1.addWidget(w1)
        # колонка 2
        col2 = QVBoxLayout(); col2.setSpacing(2)
        lbl2 = QLabel(label2); lbl2.setStyleSheet("color: #8b949e; font-size: 11px;")
        col2.addWidget(lbl2); col2.addWidget(w2)
        h.addLayout(col1)
        h.addLayout(col2)
        return h

    def _on_param_changed(self, _value=None) -> None:
        if self._auto_check.isChecked():
            self._preview_timer.start()

    def _emit_apply_canny(self) -> None:
        low = int(self._low_spin.value())
        high = int(self._high_spin.value())
        if low >= high:
            high = min(255, low + 1)
            self._high_spin.setValue(high)
        params = CannyParams(
            low_threshold=low,
            high_threshold=high,
            gauss_kernel=int(self._gauss.value()) | 1,
            dp_epsilon=float(self._eps.value()),
        )
        self.requestApplyCanny.emit(params)

    # ---------- state sync ----------

    def current_canny_params(self) -> CannyParams:
        return CannyParams(
            low_threshold=int(self._low_spin.value()),
            high_threshold=int(self._high_spin.value()),
            gauss_kernel=int(self._gauss.value()) | 1,
            dp_epsilon=float(self._eps.value()),
        )

    def set_canny_params(self, params: CannyParams) -> None:
        for w in (self._low_spin, self._high_spin, self._gauss, self._eps,
                  self._low_slider, self._high_slider):
            w.blockSignals(True)
        self._low_spin.setValue(int(params.low_threshold))
        self._low_slider.setValue(int(params.low_threshold))
        self._high_spin.setValue(int(params.high_threshold))
        self._high_slider.setValue(int(params.high_threshold))
        self._gauss.setValue(int(params.gauss_kernel) | 1)
        self._eps.setValue(float(params.dp_epsilon))
        for w in (self._low_spin, self._high_spin, self._gauss, self._eps,
                  self._low_slider, self._high_slider):
            w.blockSignals(False)

    def set_export_info(self, filename: str) -> None:
        if filename:
            self._export_info.setText(f"Сохранено: {filename}")
            self._export_info.show()
        else:
            self._export_info.hide()

    def update_state(self, state: ProjectState) -> None:
        has_project = state.project is not None
        has_image = state.image_path is not None
        has_calib = state.calibration is not None and (
            state.calibration.x1 != state.calibration.x2
            or state.calibration.y1 != state.calibration.y2
        )
        has_contours = bool(state.contours)
        has_sketch = isinstance(state.sketch, dict) and bool(state.sketch.get("entities"))

        # --- Card 1: Проект ---
        if has_project:
            self._card1.set_state(_STATE_DONE)
            name = state.project.name + (" *" if state.is_dirty else "")
            self._card1.set_value(name)
            self._btn_create.hide()
            self._btn_open.hide()
            self._btn_save.show()
            self._btn_save.setEnabled(state.is_dirty)
            _set_primary(self._btn_save, state.is_dirty)
        else:
            self._card1.set_state(_STATE_ACTIVE)
            self._card1.set_value("")
            self._btn_create.show()
            self._btn_open.show()
            self._btn_save.hide()
            _set_primary(self._btn_create, True)

        # --- Card 2: Изображение ---
        if has_image:
            self._card2.set_state(_STATE_DONE)
            self._card2.set_value(state.image_path.name)
            self._btn_import.setText("Заменить изображение…")
            _set_primary(self._btn_import, False)
            self._card2.show_content(True)
        else:
            self._card2.set_value("")
            if has_project:
                self._card2.set_state(_STATE_ACTIVE)
                self._btn_import.setText("Импортировать изображение…")
                _set_primary(self._btn_import, True)
                self._card2.show_content(True)
            else:
                self._card2.set_state(_STATE_PENDING)
                self._card2.show_content(False)

        # --- Card 3: Калибровка ---
        if has_calib:
            c = state.calibration
            self._card3.set_state(_STATE_DONE)
            self._card3.set_value(
                f"{c.real_distance:g} {c.units} ({c.scale_mm_per_pixel:.4f} мм/пкс)"
            )
            self._btn_calibrate.setText("Перекалибровать…")
            _set_primary(self._btn_calibrate, False)
            self._card3.show_content(True)
        else:
            self._card3.set_value("")
            if has_image:
                self._card3.set_state(_STATE_ACTIVE)
                self._btn_calibrate.setText("Откалибровать…")
                _set_primary(self._btn_calibrate, True)
                self._card3.show_content(True)
            else:
                self._card3.set_state(_STATE_PENDING)
                self._card3.show_content(False)

        # --- Card 4: Контуры ---
        if has_contours:
            n_total = len(state.contours)
            n_circ = sum(1 for e in state.contours if isinstance(e, Circle))
            n_poly = n_total - n_circ
            self._contours_info.setText(
                f"Найдено: {n_total} ({n_poly} полилиний, {n_circ} окружностей)"
            )
            self._contours_info.show()
            self._card4.set_state(_STATE_DONE)
        else:
            self._contours_info.hide()
            if has_image:
                self._card4.set_state(_STATE_ACTIVE)
            else:
                self._card4.set_state(_STATE_PENDING)
        self._card4.show_content(has_image)

        if state.canny_params is not None:
            current = self.current_canny_params()
            if current != state.canny_params:
                self.set_canny_params(state.canny_params)

        # --- Card 5: Эскиз ---
        if has_sketch:
            entities = state.sketch.get("entities", [])
            n_circ = sum(1 for e in entities if isinstance(e, Circle))
            n_poly = sum(1 for e in entities if isinstance(e, Polyline))
            self._sketch_info.setText(f"{n_poly} полилиний, {n_circ} окружностей")
            self._sketch_info.show()
            self._card5.set_state(_STATE_DONE)
            self._card5.show_content(True)
        else:
            self._sketch_info.hide()
            if has_contours:
                self._card5.set_state(_STATE_ACTIVE)
                self._card5.show_content(True)
            else:
                self._card5.set_state(_STATE_PENDING)
                self._card5.show_content(False)

        # --- Card 6: DXF ---
        if has_sketch:
            self._card6.set_state(_STATE_ACTIVE)
            self._card6.show_content(True)
        else:
            self._card6.set_state(_STATE_PENDING)
            self._card6.show_content(False)
