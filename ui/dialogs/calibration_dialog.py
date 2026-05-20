from __future__ import annotations

from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QSpinBox,
    QVBoxLayout,
)

from core.models import Calibration


class CalibrationDialog(QDialog):
    def __init__(self, initial: Calibration | None, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Калибровка масштаба")
        self.setModal(True)

        if initial is None:
            initial = Calibration.default()

        self._x1 = QSpinBox(); self._x1.setRange(0, 99999); self._x1.setValue(int(initial.x1))
        self._y1 = QSpinBox(); self._y1.setRange(0, 99999); self._y1.setValue(int(initial.y1))
        self._x2 = QSpinBox(); self._x2.setRange(0, 99999); self._x2.setValue(int(initial.x2))
        self._y2 = QSpinBox(); self._y2.setRange(0, 99999); self._y2.setValue(int(initial.y2))

        self._distance = QDoubleSpinBox()
        self._distance.setRange(0.01, 999999.0)
        self._distance.setDecimals(3)
        self._distance.setSingleStep(1.0)
        self._distance.setValue(float(initial.real_distance))

        self._units = QComboBox()
        self._units.addItems(["мм", "см", "м"])
        idx = self._units.findText(initial.units)
        if idx >= 0:
            self._units.setCurrentIndex(idx)

        form = QFormLayout()
        form.addRow("X1:", self._x1)
        form.addRow("Y1:", self._y1)
        form.addRow("X2:", self._x2)
        form.addRow("Y2:", self._y2)
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
    def calibration(self) -> Calibration:
        return Calibration(
            real_distance=float(self._distance.value()),
            units=self._units.currentText(),
            x1=int(self._x1.value()),
            y1=int(self._y1.value()),
            x2=int(self._x2.value()),
            y2=int(self._y2.value()),
        )
