from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QMessageBox,
    QSpinBox,
    QVBoxLayout,
)

from core.models import CannyParams


class CannyParamsDialog(QDialog):
    def __init__(self, initial: CannyParams | None, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Параметры Canny")
        self.setModal(True)

        if initial is None:
            initial = CannyParams.default()

        self._low = QSpinBox()
        self._low.setRange(0, 255)
        self._low.setValue(int(initial.low_threshold))

        self._high = QSpinBox()
        self._high.setRange(0, 255)
        self._high.setValue(int(initial.high_threshold))

        self._gauss = QSpinBox()
        self._gauss.setRange(3, 15)
        self._gauss.setSingleStep(2)
        self._gauss.setValue(int(initial.gauss_kernel) | 1)

        self._eps = QDoubleSpinBox()
        self._eps.setRange(0.1, 50.0)
        self._eps.setDecimals(2)
        self._eps.setSingleStep(0.1)
        self._eps.setValue(float(initial.dp_epsilon))

        form = QFormLayout()
        form.addRow("Нижний порог:", self._low)
        form.addRow("Верхний порог:", self._high)
        form.addRow("Ядро Гаусса:", self._gauss)
        form.addRow("Epsilon ДП:", self._eps)

        self._buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self._buttons.accepted.connect(self._on_accept)
        self._buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(self._buttons)
        self.setLayout(layout)

    @property
    def params(self) -> CannyParams:
        return CannyParams(
            low_threshold=int(self._low.value()),
            high_threshold=int(self._high.value()),
            gauss_kernel=int(self._gauss.value()) | 1,
            dp_epsilon=float(self._eps.value()),
        )

    def _on_accept(self) -> None:
        if self._low.value() >= self._high.value():
            QMessageBox.warning(self, "Проверка параметров", "Нижний порог должен быть меньше верхнего.")
            return
        self.accept()
