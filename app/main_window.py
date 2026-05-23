from __future__ import annotations

import math
from pathlib import Path

from PyQt6.QtCore import Qt, QSettings
from PyQt6.QtGui import QAction, QCloseEvent, QKeySequence
from PyQt6.QtWidgets import (
    QApplication,
    QDockWidget,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QTextEdit,
    QToolBar,
    QToolButton,
    QWidget,
)

from app.step_panel import StepPanel
from app.workspace_view import WorkspaceView
from core.contour_detector import ContourDetector
from core.database_operations import DatabaseOperations
from core.file_operations import FileOperations
from core.image_loader import ImageLoader
from core.models import Calibration, CannyParams, Circle, Polyline, Project, ProjectState
from core.sketch_generator import SketchGenerator
from ui.dialogs.about_dialog import AboutDialog
from ui.dialogs.calibration_dialog import CalibrationDialog
from ui.dialogs.db_connect_dialog import DbConnectDialog
from ui.dialogs.db_delete_dialog import DbDeleteDialog
from ui.dialogs.db_search_dialog import DbSearchDialog
from ui.dialogs.dxf_export_dialog import DxfExportDialog
from ui.dialogs.project_create_dialog import ProjectCreateDialog
from ui.dialogs.project_open_dialog import ProjectOpenDialog


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Подсистема формирования эскизов")
        self.resize(1280, 800)

        self._settings = QSettings()

        # --- Состояние и core-сервисы ---
        self._state = ProjectState()
        self._contour_detector = ContourDetector()
        self._sketch_generator = SketchGenerator()
        self._db = DatabaseOperations()

        # --- Центр: рабочая область с подложкой-подсказкой ---
        self._workspace = WorkspaceView()
        self._empty_hint = QLabel(
            "← Создайте проект, чтобы начать\n\n"
            "Логика работы:\n"
            "1. Проект  →  2. Изображение  →  3. Калибровка\n"
            "4. Контуры  →  5. Эскиз  →  6. Экспорт DXF"
        )
        self._empty_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_hint.setStyleSheet(
            "font-size: 18px; color: #8b949e; padding: 60px; line-height: 1.6;"
        )
        from PyQt6.QtWidgets import QStackedWidget
        self._center_stack = QStackedWidget()
        self._center_stack.addWidget(self._empty_hint)  # index 0
        self._center_stack.addWidget(self._workspace)    # index 1
        self.setCentralWidget(self._center_stack)

        # --- Левая панель шагов (как QDockWidget — недвигаемый) ---
        self._step_panel = StepPanel()
        dock_steps = QDockWidget("Шаги", self)
        dock_steps.setObjectName("dock_steps")
        dock_steps.setWidget(self._step_panel)
        dock_steps.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        dock_steps.setTitleBarWidget(QWidget())  # скрыть title bar
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock_steps)

        # --- Журнал (скрыт по умолчанию) ---
        self._log_view = QTextEdit()
        self._log_view.setReadOnly(True)
        self._log_view.setPlaceholderText("Журнал действий.")
        self._dock_log = QDockWidget("Журнал", self)
        self._dock_log.setObjectName("dock_log")
        self._dock_log.setWidget(self._log_view)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self._dock_log)
        self._dock_log.setVisible(False)

        # --- Статус-бар: сообщения слева, инфо справа ---
        self._status_zoom = QLabel("100%")
        self._status_pos = QLabel("Х: 0   У: 0")
        self._status_img = QLabel("—")
        for w in (self._status_img, self._status_pos, self._status_zoom):
            w.setStyleSheet("color: #57606a; padding: 0 8px;")
        self.statusBar().addPermanentWidget(self._status_img)
        self.statusBar().addPermanentWidget(self._status_pos)
        self.statusBar().addPermanentWidget(self._status_zoom)
        self.statusBar().showMessage("Готово")

        # --- Сигналы workspace ---
        self._workspace.zoomChanged.connect(self._on_zoom_changed)
        self._workspace.mouseScenePosChanged.connect(self._on_mouse_pos_changed)
        self._workspace.calibrationPoint1Set.connect(self._on_calib_point1)
        self._workspace.calibrationCompleted.connect(self._on_calib_completed)
        self._workspace.calibrationCancelled.connect(self._on_calib_cancelled)

        # --- Сигналы StepPanel ---
        self._step_panel.requestCreateProject.connect(self._on_project_create)
        self._step_panel.requestOpenProject.connect(self._on_project_open)
        self._step_panel.requestSaveProject.connect(self._on_project_save)
        self._step_panel.requestImportImage.connect(self._on_image_import)
        self._step_panel.requestStartCalibration.connect(self._on_calibration)
        self._step_panel.requestApplyCanny.connect(self._on_canny_apply)
        self._step_panel.requestBuildSketch.connect(self._on_sketch_build)
        self._step_panel.requestExportDxf.connect(self._on_export_dxf)

        # --- Тулбар ---
        self._build_toolbar()

        # --- Изначальная синхронизация ---
        self._refresh_all()

    # ============================================================ Toolbar

    def _build_toolbar(self) -> None:
        tb = QToolBar("Главная панель")
        tb.setMovable(False)
        tb.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.addToolBar(tb)

        self._act_save = QAction("💾  Сохранить", self)
        self._act_save.setShortcut(QKeySequence.StandardKey.Save)
        self._act_save.triggered.connect(self._on_project_save)
        tb.addAction(self._act_save)

        self._act_open = QAction("📂  Открыть…", self)
        self._act_open.setShortcut(QKeySequence.StandardKey.Open)
        self._act_open.triggered.connect(self._on_project_open)
        tb.addAction(self._act_open)

        self._act_close = QAction("✕  Закрыть проект", self)
        self._act_close.triggered.connect(self._on_project_close)
        tb.addAction(self._act_close)

        tb.addSeparator()

        more_btn = QToolButton()
        more_btn.setText("☰  Меню")
        more_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        more_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        more_menu = QMenu(more_btn)

        # БД
        db_menu = more_menu.addMenu("База данных")
        db_menu.addAction("Подключение…", self._on_db_connect)
        db_menu.addAction("Поиск…", self._on_db_search)
        db_menu.addAction("Удаление…", self._on_db_delete)

        # Вид
        view_menu = more_menu.addMenu("Вид")
        act_fit = view_menu.addAction("Подогнать по окну", self._workspace.fit_to_view)
        act_fit.setShortcut(QKeySequence("F"))
        act_in = view_menu.addAction("Увеличить", self._workspace.zoom_in)
        act_in.setShortcut(QKeySequence.StandardKey.ZoomIn)
        act_out = view_menu.addAction("Уменьшить", self._workspace.zoom_out)
        act_out.setShortcut(QKeySequence.StandardKey.ZoomOut)
        act_100 = view_menu.addAction("100%", self._workspace.zoom_100)
        act_100.setShortcut(QKeySequence("Ctrl+0"))
        view_menu.addSeparator()
        self._act_toggle_log = QAction("Показать журнал", self, checkable=True)
        self._act_toggle_log.toggled.connect(self._dock_log.setVisible)
        self._dock_log.visibilityChanged.connect(self._act_toggle_log.setChecked)
        view_menu.addAction(self._act_toggle_log)

        more_menu.addSeparator()
        more_menu.addAction("О программе", self._on_about)
        more_menu.addSeparator()
        act_quit = QAction("Выход", self)
        act_quit.setShortcut(QKeySequence.StandardKey.Quit)
        act_quit.triggered.connect(self.close)
        more_menu.addAction(act_quit)

        more_btn.setMenu(more_menu)
        tb.addWidget(more_btn)

        # Регистрируем shortcut'ы на main window (через QAction) чтобы работали в любом месте
        for act in (act_fit, act_in, act_out, act_100):
            self.addAction(act)

    # ============================================================ Lifecycle

    def closeEvent(self, event: QCloseEvent) -> None:
        if not self._maybe_handle_unsaved():
            event.ignore()
            return
        super().closeEvent(event)

    def keyPressEvent(self, event) -> None:  # type: ignore[override]
        if event.key() == Qt.Key.Key_Escape and self._workspace.is_calibration_mode():
            self._workspace.set_calibration_mode(False)
            self._workspace.calibrationCancelled.emit()
            event.accept()
            return
        super().keyPressEvent(event)

    # ============================================================ Project

    def _on_project_create(self) -> None:
        if not self._maybe_handle_unsaved():
            return
        dlg = ProjectCreateDialog(self)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return
        project = Project(name=dlg.project_name, project_file=dlg.project_file)
        self._state = ProjectState(project=project, is_dirty=True)
        self._workspace.clear_all()
        self._log(f"Создан проект: {project.project_file}")
        self.statusBar().showMessage(f"Проект создан: {project.name}")
        self._refresh_all()

    def _on_project_open(self) -> None:
        if not self._maybe_handle_unsaved():
            return
        dlg = ProjectOpenDialog(self)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return
        try:
            state = FileOperations.load_project_state(dlg.project_file)
        except Exception as e:  # noqa: BLE001
            self._show_error("Не удалось открыть проект", str(e))
            return
        self._state = state
        self._workspace.clear_all()
        # Если есть путь к изображению — загрузим
        if self._state.image_path is not None and self._state.image_path.exists():
            try:
                self._workspace.set_image(ImageLoader.load(self._state.image_path))
            except Exception as e:  # noqa: BLE001
                self._log(f"Изображение не загружено: {e}")
        self._log(f"Открыт проект: {state.project.project_file}")
        self.statusBar().showMessage(f"Проект открыт: {state.project.name}")
        self._refresh_all()

    def _on_project_save(self) -> None:
        if self._state.project is None:
            return
        try:
            FileOperations.save_project(self._state)
        except Exception as e:  # noqa: BLE001
            self._show_error("Не удалось сохранить проект", str(e))
            return
        self._state.is_dirty = False
        self._log(f"Проект сохранён: {self._state.project.project_file}")
        self.statusBar().showMessage("Проект сохранён")
        self._refresh_all()

    def _on_project_close(self) -> None:
        if self._state.project is None:
            return
        if not self._maybe_handle_unsaved():
            return
        self._state = ProjectState()
        self._workspace.clear_all()
        self._log("Проект закрыт")
        self.statusBar().showMessage("Проект закрыт")
        self._refresh_all()

    # ============================================================ Image

    def _on_image_import(self) -> None:
        if self._state.project is None:
            return
        start_dir = str(self._state.project.project_file.parent)
        last_dir = self._settings.value("paths/import_dir", "", type=str) or start_dir
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Импорт изображения",
            last_dir,
            "Изображения (*.jpg *.jpeg *.png *.bmp *.tif *.tiff);;Все файлы (*.*)",
        )
        if not file_name:
            return
        path = Path(file_name)
        if path.suffix.lower() == ".svg":
            self._show_warning("Ограничение формата", "SVG не поддерживается.")
            return
        try:
            image = ImageLoader.load(path)
            self._workspace.set_image(image)
        except Exception as e:  # noqa: BLE001
            self._show_error("Не удалось загрузить изображение", str(e))
            return
        self._state.image_path = path
        self._state.contours = None
        self._state.sketch = None
        self._state.is_dirty = True
        self._settings.setValue("paths/import_dir", str(path.parent))
        self._log(f"Импортировано: {path}")
        self.statusBar().showMessage(f"Загружено: {path.name}")
        self._refresh_all()

    # ============================================================ Calibration

    def _on_calibration(self) -> None:
        if self._state.project is None or self._state.image_path is None:
            return
        self._workspace.set_calibration_mode(True)
        self.statusBar().showMessage("Калибровка: кликните первую точку на изображении")
        self._log("Режим калибровки активирован")

    def _on_calib_point1(self, x: int, y: int) -> None:
        self.statusBar().showMessage(
            f"Калибровка: первая точка ({x}, {y}) — кликните вторую точку"
        )

    def _on_calib_completed(self, x1: int, y1: int, x2: int, y2: int) -> None:
        pixel_dist = math.hypot(x2 - x1, y2 - y1)
        if pixel_dist < 1.0:
            self._show_warning("Калибровка", "Точки слишком близко.")
            self._workspace.set_calibration_mode(False)
            return
        dlg = CalibrationDialog(
            pixel_distance=pixel_dist,
            initial=self._state.calibration,
            parent=self,
        )
        accepted = dlg.exec() == dlg.DialogCode.Accepted
        self._workspace.set_calibration_mode(False)
        if not accepted:
            self.statusBar().showMessage("Калибровка отменена")
            self._log("Калибровка отменена")
            return
        self._state.calibration = Calibration(
            real_distance=dlg.real_distance,
            units=dlg.units,
            x1=x1, y1=y1, x2=x2, y2=y2,
        )
        self._state.is_dirty = True
        scale = self._state.calibration.scale_mm_per_pixel
        self._log(
            f"Калибровка: {dlg.real_distance:g} {dlg.units} "
            f"({pixel_dist:.1f} px → {scale:.4f} мм/пкс)"
        )
        self.statusBar().showMessage(f"Калибровка: {dlg.real_distance:g} {dlg.units}")
        self._refresh_all()

    def _on_calib_cancelled(self) -> None:
        self.statusBar().showMessage("Калибровка отменена")
        self._log("Калибровка отменена")

    # ============================================================ Canny (live)

    def _on_canny_apply(self, params: CannyParams) -> None:
        if self._state.project is None or self._state.image_path is None:
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            contours = self._contour_detector.detect(self._state.image_path, params)
        except Exception as e:  # noqa: BLE001
            QApplication.restoreOverrideCursor()
            self._show_error("Не удалось выделить контуры", str(e))
            return
        QApplication.restoreOverrideCursor()

        self._state.canny_params = params
        self._state.contours = contours
        self._state.sketch = None  # сбрасываем старый эскиз
        self._state.is_dirty = True

        self._workspace.show_contours(contours)
        self._workspace.show_sketch([])
        n = len(contours)
        n_circ = sum(1 for e in contours if isinstance(e, Circle))
        self._log(
            f"Canny: {params.low_threshold}/{params.high_threshold}, "
            f"gauss={params.gauss_kernel}, eps={params.dp_epsilon:.2f}, "
            f"контуров: {n} (окружностей: {n_circ})"
        )
        self.statusBar().showMessage(f"Контуры: {n}")
        self._refresh_all()

    # ============================================================ Sketch

    def _on_sketch_build(self) -> None:
        if self._state.project is None or not self._state.contours:
            return
        self._state.sketch = self._sketch_generator.build(
            self._state.contours, calibration=self._state.calibration
        )
        self._state.is_dirty = True
        entities = self._state.sketch.get("entities", [])
        if isinstance(entities, list):
            self._workspace.show_sketch(entities)
        self._log(f"Эскиз построен ({len(entities)} элементов)")
        self.statusBar().showMessage("Эскиз построен")
        self._refresh_all()

    # ============================================================ DXF

    def _on_export_dxf(self) -> None:
        if self._state.project is None:
            return
        entities: list[Polyline | Circle] = []
        if isinstance(self._state.sketch, dict):
            raw = self._state.sketch.get("entities", [])
            if isinstance(raw, list):
                entities = [e for e in raw if isinstance(e, (Polyline, Circle))]
        if not entities:
            self._show_warning("Экспорт DXF", "Сначала постройте эскиз (шаг 5).")
            return
        dlg = DxfExportDialog(project_name=self._state.project.name, parent=self)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return
        try:
            FileOperations.export_dxf_placeholder(
                target_file=dlg.target_file,
                polylines=entities,
                project=self._state.project,
                calibration=self._state.calibration or Calibration.default(),
                canny_params=self._state.canny_params or CannyParams.default(),
            )
        except Exception as e:  # noqa: BLE001
            self._show_error("Экспорт DXF не выполнен", str(e))
            return
        self._settings.setValue("paths/export_dir", str(dlg.target_file.parent))
        self._log(f"DXF экспортирован: {dlg.target_file}")
        self._step_panel.set_export_info(dlg.target_file.name)

        if self._db.is_connected and self._state.image_path is not None:
            try:
                rec_id = self._db.save_image_record(
                    image_path=self._state.image_path,
                    calibration=self._state.calibration or Calibration.default(),
                    canny=self._state.canny_params or CannyParams.default(),
                    dxf_path=dlg.target_file,
                )
                self._log(f"БД: запись сохранена (id={rec_id})")
            except Exception as e:  # noqa: BLE001
                self._show_warning("БД", f"Не удалось сохранить в БД: {e}")

        self.statusBar().showMessage(f"DXF: {dlg.target_file.name}")
        QMessageBox.information(self, "Экспорт DXF", f"Файл создан:\n{dlg.target_file}")

    # ============================================================ DB

    def _on_db_connect(self) -> None:
        dlg = DbConnectDialog(self)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return
        try:
            self._db.connect(dlg.database)
        except Exception as e:  # noqa: BLE001
            self._show_error("БД", f"Подключение не выполнено: {e}")
            return
        self._log(f"БД: подключение к {dlg.database}")
        QMessageBox.information(self, "База данных", "Подключение выполнено.")

    def _on_db_search(self) -> None:
        if not self._db.is_connected:
            self._show_warning("База данных", "Сначала подключитесь к БД.")
            return
        dlg = DbSearchDialog(self)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return
        results = self._db.search(dlg.query)
        self._log(f"БД: поиск '{dlg.query}', найдено {len(results)}")
        if not results:
            QMessageBox.information(self, "База данных", f"По запросу «{dlg.query}» ничего не найдено.")
            return
        text = f"Найдено: {len(results)}\n\n"
        for r in results[:20]:
            text += f"id={r['id']}: {r['path']}  ({r['date']})\n"
        if len(results) > 20:
            text += f"\n…и ещё {len(results) - 20}"
        QMessageBox.information(self, "База данных", text)

    def _on_db_delete(self) -> None:
        if not self._db.is_connected:
            self._show_warning("База данных", "Сначала подключитесь к БД.")
            return
        dlg = DbDeleteDialog(self)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return
        ok = self._db.delete(dlg.record_id)
        if ok:
            self._log(f"БД: удаление ID={dlg.record_id}")
            QMessageBox.information(self, "База данных", f"Удалено: ID={dlg.record_id}")
        else:
            QMessageBox.warning(self, "База данных", "Запись не найдена.")

    # ============================================================ About

    def _on_about(self) -> None:
        AboutDialog(self).exec()

    # ============================================================ Refresh

    def _refresh_all(self) -> None:
        # Состояние действий тулбара
        has_project = self._state.project is not None
        self._act_save.setEnabled(has_project and self._state.is_dirty)
        self._act_close.setEnabled(has_project)
        # Центр: подсказка или рабочая область
        self._center_stack.setCurrentIndex(1 if has_project else 0)
        # Заголовок
        if has_project:
            dirty = "* " if self._state.is_dirty else ""
            self.setWindowTitle(f"{dirty}{self._state.project.name} — Подсистема эскизов")
        else:
            self.setWindowTitle("Подсистема формирования эскизов")
        # Размер изображения в статус-баре
        if self._state.image_path is not None:
            w, h = self._workspace.image_size()
            self._status_img.setText(f"{w}×{h}")
        else:
            self._status_img.setText("—")
        # StepPanel
        self._step_panel.update_state(self._state)

    # ============================================================ Helpers

    def _log(self, message: str) -> None:
        self._log_view.append(message)

    def _on_zoom_changed(self, z: float) -> None:
        self._status_zoom.setText(f"{int(z * 100)}%")

    def _on_mouse_pos_changed(self, p) -> None:
        self._status_pos.setText(f"Х: {p.x():.0f}   У: {p.y():.0f}")

    def _maybe_handle_unsaved(self) -> bool:
        if self._state.project is None or not self._state.is_dirty:
            return True
        answer = QMessageBox.question(
            self,
            "Несохранённые изменения",
            "Сохранить проект?",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Yes,
        )
        if answer == QMessageBox.StandardButton.Cancel:
            return False
        if answer == QMessageBox.StandardButton.No:
            return True
        self._on_project_save()
        return not self._state.is_dirty

    def _show_error(self, title: str, message: str) -> None:
        QMessageBox.critical(self, title, message)
        self.statusBar().showMessage(title)

    def _show_warning(self, title: str, message: str) -> None:
        QMessageBox.warning(self, title, message)
        self.statusBar().showMessage(title)
