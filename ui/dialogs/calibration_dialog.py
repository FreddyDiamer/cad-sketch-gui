"""Диалог ввода реального расстояния между двумя опорными точками.

Открывается после того, как пользователь кликнул две точки прямо на
изображении (см. WorkspaceView). В диалоге показано пиксельное
расстояние (read-only) и предлагается ввести реальное расстояние
с выбором единиц измерения (мм/см/м).
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QVBoxLayout,
)

from core.models import Calibration


class CalibrationDialog(QDialog):
    """Диалог ввода реального расстояния после клика двух точек на изображении."""

    def __init__(
        self,
        pixel_distance: float,
        initial: Calibration | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Калибровка масштаба")
        self.setModal(True)

        self._pixel_distance = float(pixel_distance)

        # Информационная строка — только для чтения.
        self._pixel_lbl = QLabel(f"{self._pixel_distance:.1f} пикс.")

        # Поле ввода реального расстояния: 3 знака после запятой,
        # положительные значения. При перекалибровке подставляется прошлое.
        self._distance = QDoubleSpinBox()
        self._distance.setRange(0.01, 999999.0)
        self._distance.setDecimals(3)
        self._distance.setSingleStep(1.0)
        self._distance.setValue(float(initial.real_distance) if initial else 50.0)

        # Единицы измерения, в которых пользователь задал расстояние.
        # При вычислении масштаба они приводятся к миллиметрам.
        self._units = QComboBox()
        self._units.addItems(["мм", "см", "м"])
        if initial is not None:
            idx = self._units.findText(initial.units)
            if idx >= 0:
                self._units.setCurrentIndex(idx)

        form = QFormLayout()
        form.addRow("Расстояние в пикселях:", self._pixel_lbl)
        form.addRow("Реальное расстояние:", self._distance)
        form.addRow("Единицы:", self._units)

        self._buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(self._buttons)
        self.setLayout(layout)

    @property
    def pixel_distance(self) -> float:
        return self._pixel_distance

    @property
    def real_distance(self) -> float:
        return float(self._distance.value())

    @property
    def units(self) -> str:
        return self._units.currentText()
