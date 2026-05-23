from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtCore import Qt, QSettings
from PyQt6.QtGui import QAction, QCloseEvent, QKeySequence
from PyQt6.QtWidgets import (
    QDockWidget,
    QFileDialog,
    QFormLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QTextEdit,
    QToolBar,
    QVBoxLayout,
    QWidget,
    QStyle,
)

from app.workspace_view import WorkspaceView
from app.welcome_widget import WelcomeWidget
from core.contour_detector import ContourDetector
from core.database_operations import DatabaseOperations
from core.file_operations import FileOperations
from core.image_loader import ImageLoader
from core.models import Calibration, CannyParams, Circle, Polyline, Project, ProjectState
from core.sketch_generator import SketchGenerator
from ui.dialogs.about_dialog import AboutDialog
from ui.dialogs.calibration_dialog import CalibrationDialog
from ui.dialogs.canny_params_dialog import CannyParamsDialog
from ui.dialogs.db_connect_dialog import DbConnectDialog
from ui.dialogs.db_delete_dialog import DbDeleteDialog
from ui.dialogs.db_search_dialog import DbSearchDialog
from ui.dialogs.dxf_export_dialog import DxfExportDialog
from ui.dialogs.project_create_dialog import ProjectCreateDialog
from ui.dialogs.project_open_dialog import ProjectOpenDialog


@dataclass(frozen=True)
class _ActionBundle:
    project_new: QAction
    project_open: QAction
    project_save: QAction
    project_close: QAction
    project_exit: QAction

    image_import: QAction
    image_calibrate: QAction

    process_canny: QAction

    sketch_build: QAction
    sketch_export_dxf: QAction

    db_connect: QAction
    db_search: QAction
    db_delete: QAction

    help_about: QAction

    view_fit: QAction
    view_zoom_in: QAction
    view_zoom_out: QAction
    view_zoom_100: QAction


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Подсистема формирования эскизов")
        self.resize(1100, 700)

        self._settings = QSettings()

        self._state = ProjectState()
        self._workspace = WorkspaceView()
        self._welcome = WelcomeWidget()
        self._welcome.createRequested.connect(self._on_project_create)
        self._welcome.openRequested.connect(self._on_project_open)

        self._center_stack = QStackedWidget()
        self._center_stack.addWidget(self._welcome)   # index 0
        self._center_stack.addWidget(self._workspace)  # index 1
        self.setCentralWidget(self._center_stack)

        self._contour_detector = ContourDetector()
        self._sketch_generator = SketchGenerator()
        self._db = DatabaseOperations()

        self._status_zoom = QLabel("Масштаб: 100%")
        self._status_pos = QLabel("X: —  Y: —")
        self._status_img = QLabel("Изображение: —")
        self.statusBar().addPermanentWidget(self._status_img)
        self.statusBar().addPermanentWidget(self._status_pos)
        self.statusBar().addPermanentWidget(self._status_zoom)
        self.statusBar().showMessage("Готово")

        self._workspace.zoomChanged.connect(self._on_zoom_changed)
        self._workspace.mouseScenePosChanged.connect(self._on_mouse_pos_changed)

        self._actions = self._build_actions()
        self._build_menus(self._actions)
        self._build_toolbar(self._actions)
        self._build_docks()
        self._apply_action_state()
        self._refresh_project_panel()
        self._refresh_title()

    # --- UI wiring ---

    def _build_actions(self) -> _ActionBundle:
        style = self.style()

        # Проект
        act_project_new = QAction("Создать…", self)
        act_project_new.setStatusTip("Создать новый проект")
        act_project_new.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_FileIcon))
        act_project_new.triggered.connect(self._on_project_create)

        act_project_open = QAction("Открыть…", self)
        act_project_open.setStatusTip("Открыть существующий проект")
        act_project_open.setShortcut(QKeySequence.StandardKey.Open)
        act_project_open.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton))
        act_project_open.triggered.connect(self._on_project_open)

        act_project_save = QAction("Сохранить", self)
        act_project_save.setStatusTip("Сохранить проект")
        act_project_save.setShortcut(QKeySequence.StandardKey.Save)
        act_project_save.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))
        act_project_save.triggered.connect(self._on_project_save)

        act_project_close = QAction("Закрыть", self)
        act_project_close.setStatusTip("Закрыть текущий проект")
        act_project_close.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_DialogCloseButton))
        act_project_close.triggered.connect(self._on_project_close)

        act_project_exit = QAction("Выход", self)
        act_project_exit.setStatusTip("Выйти из приложения")
        act_project_exit.setShortcut(QKeySequence.StandardKey.Quit)
        act_project_exit.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_BrowserStop))
        act_project_exit.triggered.connect(self.close)

        # Изображение
        act_image_import = QAction("Импорт изображения…", self)
        act_image_import.setStatusTip("Импортировать изображение (без SVG/PNG)")
        act_image_import.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_ArrowUp))
        act_image_import.triggered.connect(self._on_image_import)

        act_image_calibrate = QAction("Калибровка…", self)
        act_image_calibrate.setStatusTip("Задать масштаб (реальное расстояние)")
        act_image_calibrate.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton))
        act_image_calibrate.triggered.connect(self._on_calibration)

        # Обработка
        act_process_canny = QAction("Выделение контуров (Canny)…", self)
        act_process_canny.setStatusTip("Запустить выделение контуров")
        act_process_canny.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_CommandLink))
        act_process_canny.triggered.connect(self._on_canny)

        # Эскиз
        act_sketch_build = QAction("Построение эскиза", self)
        act_sketch_build.setStatusTip("Сформировать эскиз по контурам")
        act_sketch_build.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView))
        act_sketch_build.triggered.connect(self._on_sketch_build)

        act_sketch_export = QAction("Экспорт DXF…", self)
        act_sketch_export.setStatusTip("Экспортировать эскиз в DXF (placeholder)")
        act_sketch_export.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))
        act_sketch_export.triggered.connect(self._on_export_dxf)

        # База данных
        act_db_connect = QAction("Подключение…", self)
        act_db_connect.setStatusTip("Подключение к базе данных")
        act_db_connect.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_DriveNetIcon))
        act_db_connect.triggered.connect(self._on_db_connect)

        act_db_search = QAction("Поиск…", self)
        act_db_search.setStatusTip("Поиск по базе данных")
        act_db_search.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_FileDialogContentsView))
        act_db_search.triggered.connect(self._on_db_search)

        act_db_delete = QAction("Удаление…", self)
        act_db_delete.setStatusTip("Удаление записи из базы данных")
        act_db_delete.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_TrashIcon))
        act_db_delete.triggered.connect(self._on_db_delete)

        # Справка
        act_help_about = QAction("О программе", self)
        act_help_about.setStatusTip("Информация о программе")
        act_help_about.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_MessageBoxInformation))
        act_help_about.triggered.connect(self._on_about)

        # Вид (удобство, без усложнений)
        act_view_fit = QAction("Подогнать по окну", self)
        act_view_fit.setStatusTip("Подогнать изображение по окну")
        act_view_fit.setShortcut(QKeySequence("F"))
        act_view_fit.triggered.connect(self._workspace.fit_to_view)

        act_view_zoom_in = QAction("Увеличить", self)
        act_view_zoom_in.setShortcut(QKeySequence.StandardKey.ZoomIn)
        act_view_zoom_in.triggered.connect(self._workspace.zoom_in)

        act_view_zoom_out = QAction("Уменьшить", self)
        act_view_zoom_out.setShortcut(QKeySequence.StandardKey.ZoomOut)
        act_view_zoom_out.triggered.connect(self._workspace.zoom_out)

        act_view_zoom_100 = QAction("100%", self)
        act_view_zoom_100.setStatusTip("Сброс масштаба до 100%")
        act_view_zoom_100.setShortcut(QKeySequence("Ctrl+0"))
        act_view_zoom_100.triggered.connect(self._workspace.zoom_100)

        return _ActionBundle(
            project_new=act_project_new,
            project_open=act_project_open,
            project_save=act_project_save,
            project_close=act_project_close,
            project_exit=act_project_exit,
            image_import=act_image_import,
            image_calibrate=act_image_calibrate,
            process_canny=act_process_canny,
            sketch_build=act_sketch_build,
            sketch_export_dxf=act_sketch_export,
            db_connect=act_db_connect,
            db_search=act_db_search,
            db_delete=act_db_delete,
            help_about=act_help_about,
            view_fit=act_view_fit,
            view_zoom_in=act_view_zoom_in,
            view_zoom_out=act_view_zoom_out,
            view_zoom_100=act_view_zoom_100,
        )

    def _build_menus(self, a: _ActionBundle) -> None:
        menu_project = self.menuBar().addMenu("Проект")
        menu_project.addAction(a.project_new)
        menu_project.addAction(a.project_open)
        menu_project.addSeparator()
        menu_project.addAction(a.project_save)
        menu_project.addAction(a.project_close)
        menu_project.addSeparator()
        menu_project.addAction(a.project_exit)

        menu_image = self.menuBar().addMenu("Изображение")
        menu_image.addAction(a.image_import)
        menu_image.addAction(a.image_calibrate)
        menu_image.addSeparator()
        menu_image.addAction(a.view_fit)
        menu_image.addAction(a.view_zoom_in)
        menu_image.addAction(a.view_zoom_out)
        menu_image.addAction(a.view_zoom_100)

        menu_process = self.menuBar().addMenu("Обработка")
        menu_process.addAction(a.process_canny)

        menu_sketch = self.menuBar().addMenu("Эскиз")
        menu_sketch.addAction(a.sketch_build)
        menu_sketch.addAction(a.sketch_export_dxf)

        menu_db = self.menuBar().addMenu("База данных")
        menu_db.addAction(a.db_connect)
        menu_db.addAction(a.db_search)
        menu_db.addAction(a.db_delete)

        menu_help = self.menuBar().addMenu("Справка")
        menu_help.addAction(a.help_about)

    def _build_toolbar(self, a: _ActionBundle) -> None:
        tb = QToolBar("Инструменты")
        tb.setMovable(False)
        tb.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        self.addToolBar(tb)

        tb.addAction(a.image_import)
        tb.addAction(a.image_calibrate)
        tb.addSeparator()
        tb.addAction(a.view_fit)
        tb.addAction(a.view_zoom_in)
        tb.addAction(a.view_zoom_out)
        tb.addAction(a.view_zoom_100)
        tb.addSeparator()
        tb.addAction(a.process_canny)
        tb.addSeparator()
        tb.addAction(a.sketch_build)
        tb.addAction(a.sketch_export_dxf)

    def _apply_action_state(self) -> None:
        has_project = self._state.project is not None
        has_image = self._state.image_path is not None
        has_contours = self._state.contours is not None
        has_sketch = self._state.sketch is not None

        self._actions.project_save.setEnabled(has_project)
        self._actions.project_close.setEnabled(has_project)

        self._actions.image_import.setEnabled(has_project)
        self._actions.image_calibrate.setEnabled(has_project and has_image)

        self._actions.process_canny.setEnabled(has_project and has_image)
        self._actions.sketch_build.setEnabled(has_project and has_contours)

        # Экспорт делаем доступным и для пустого эскиза (placeholder),
        # но всё равно требуем проект, чтобы был контекст.
        self._actions.sketch_export_dxf.setEnabled(has_project and (has_sketch or has_image))

        self._actions.db_search.setEnabled(True)
        self._actions.db_delete.setEnabled(True)

        # Центральная область: либо стартовый экран, либо рабочая область
        self._center_stack.setCurrentIndex(1 if has_project else 0)

    def _build_docks(self) -> None:
        # Док "Проект"
        self._project_name_lbl = QLabel("—")
        self._project_file_lbl = QLabel("—")
        self._image_lbl = QLabel("—")
        self._calib_lbl = QLabel("—")
        self._canny_lbl = QLabel("—")
        self._contours_lbl = QLabel("—")
        self._sketch_lbl = QLabel("—")

        form = QFormLayout()
        form.addRow("Проект:", self._project_name_lbl)
        form.addRow("Файл:", self._project_file_lbl)
        form.addRow("Изображение:", self._image_lbl)
        form.addRow("Калибровка:", self._calib_lbl)
        form.addRow("Canny:", self._canny_lbl)
        form.addRow("Контуры:", self._contours_lbl)
        form.addRow("Эскиз:", self._sketch_lbl)

        box = QWidget()
        box.setLayout(form)

        dock_project = QDockWidget("Панель проекта", self)
        dock_project.setObjectName("dock_project")
        dock_project.setWidget(box)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock_project)

        # Док "Журнал"
        self._log_view = QTextEdit()
        self._log_view.setReadOnly(True)
        self._log_view.setPlaceholderText("Здесь отображаются действия пользователя и сообщения системы.")
        dock_log = QDockWidget("Журнал", self)
        dock_log.setObjectName("dock_log")
        dock_log.setWidget(self._log_view)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, dock_log)

    def closeEvent(self, event: QCloseEvent) -> None:
        if not self._maybe_handle_unsaved():
            event.ignore()
            return
        super().closeEvent(event)

    # --- Handlers ---

    def _on_project_create(self) -> None:
        dlg = ProjectCreateDialog(self)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return

        project = Project(name=dlg.project_name, project_file=dlg.project_file)
        # Автокалибровка: ставим значение по умолчанию сразу при создании проекта.
        self._state = ProjectState(project=project, calibration=Calibration.default(), is_dirty=True)
        self._workspace.clear_all()
        self._log(f"Создан проект: {project.project_file}")
        self._log("Калибровка применена автоматически")
        self.statusBar().showMessage(f"Проект создан: {project.name}")
        self._apply_action_state()
        self._refresh_project_panel()
        self._refresh_title()

    def _on_project_open(self) -> None:
        if not self._maybe_handle_unsaved():
            return

        dlg = ProjectOpenDialog(self)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return

        try:
            state = FileOperations.load_project_state(dlg.project_file)
        except Exception as e:  # noqa: BLE001 - показываем ошибку пользователю
            self._show_error("Не удалось открыть проект", str(e))
            return

        self._state = state
        project = state.project
        self._workspace.clear_all()
        self._log(f"Открыт проект: {project.project_file}")
        self.statusBar().showMessage(f"Проект открыт: {project.name}")
        self._apply_action_state()
        self._refresh_project_panel()
        self._refresh_title()

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
        self._refresh_title()
        self._refresh_project_panel()

    def _on_project_close(self) -> None:
        if self._state.project is None:
            return

        if not self._maybe_handle_unsaved():
            return

        self._state = ProjectState()
        self._workspace.clear_all()
        self._log("Проект закрыт")
        self.statusBar().showMessage("Проект закрыт")
        self._apply_action_state()
        self._refresh_project_panel()
        self._refresh_title()

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
        if self._state.calibration is None:
            # Автокалибровка: применяем при первом импорте изображения.
            self._state.calibration = Calibration.default()
            self._log("Калибровка применена автоматически")
        self._settings.setValue("paths/import_dir", str(path.parent))
        self._log(f"Импортировано изображение: {path}")
        self.statusBar().showMessage(f"Загружено изображение: {path.name}")
        self._apply_action_state()
        self._refresh_project_panel()
        self._refresh_title()
        self._refresh_image_status()

    def _on_calibration(self) -> None:
        if self._state.project is None or self._state.image_path is None:
            return

        dlg = CalibrationDialog(initial=self._state.calibration, parent=self)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return

        self._state.calibration = dlg.calibration
        self._state.is_dirty = True
        self._log(f"Калибровка: {dlg.calibration.real_distance:g} {dlg.calibration.units}")
        self.statusBar().showMessage(
            f"Калибровка задана: {dlg.calibration.real_distance:g} {dlg.calibration.units}"
        )
        self._refresh_project_panel()
        self._refresh_title()

    def _on_canny(self) -> None:
        if self._state.project is None or self._state.image_path is None:
            return

        dlg = CannyParamsDialog(initial=self._state.canny_params, parent=self)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return

        self._state.canny_params = dlg.params

        try:
            contours = self._contour_detector.detect(self._state.image_path, dlg.params)
        except Exception as e:  # noqa: BLE001
            self._show_error("Выделение контуров не выполнено", str(e))
            return

        self._state.contours = contours
        self._state.sketch = None
        self._state.is_dirty = True

        self._workspace.show_contours(contours)
        self._workspace.show_sketch([])  # очищаем слой эскиза
        self._log(
            f"Canny: {dlg.params.low_threshold}/{dlg.params.high_threshold}, "
            f"gauss={dlg.params.gauss_kernel}, eps={dlg.params.dp_epsilon:.2f}, "
            f"контуров: {len(contours)}"
        )
        if not contours:
            self._show_warning(
                "Контуры не найдены",
                "Алгоритм не нашёл контуров. Попробуйте изменить пороги или ядро Гаусса.",
            )
        self.statusBar().showMessage(
            f"Контуры получены ({len(contours)}). Пороги: "
            f"{dlg.params.low_threshold} / {dlg.params.high_threshold}"
        )
        self._apply_action_state()
        self._refresh_project_panel()
        self._refresh_title()

    def _on_sketch_build(self) -> None:
        if self._state.project is None or self._state.contours is None:
            return

        self._state.sketch = self._sketch_generator.build(
            self._state.contours, calibration=self._state.calibration
        )
        self._state.is_dirty = True
        self._log("Эскиз построен")
        entities = self._state.sketch.get("entities", []) if isinstance(self._state.sketch, dict) else []
        if isinstance(entities, list):
            self._workspace.show_sketch(entities)
        self.statusBar().showMessage("Эскиз построен")
        self._apply_action_state()
        self._refresh_project_panel()
        self._refresh_title()

    def _on_export_dxf(self) -> None:
        if self._state.project is None:
            return

        dlg = DxfExportDialog(project_name=self._state.project.name, parent=self)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return

        entities: list[Polyline | Circle] = []
        if isinstance(self._state.sketch, dict):
            raw = self._state.sketch.get("entities", [])
            if isinstance(raw, list):
                entities = [e for e in raw if isinstance(e, (Polyline, Circle))]

        if not entities:
            self._show_warning(
                "Экспорт DXF",
                "Нет полилиний для экспорта. Постройте эскиз перед экспортом.",
            )
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
                self._show_warning("БД", f"Не удалось сохранить запись в БД: {e}")

        QMessageBox.information(self, "Экспорт DXF", f"Файл создан:\n{dlg.target_file}")
        self.statusBar().showMessage("DXF экспортирован")

    def _on_db_connect(self) -> None:
        dlg = DbConnectDialog(self)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return
        self._db.connect(dlg.host, dlg.database, dlg.user, dlg.password)
        self._log(f"БД: подключение к {dlg.host}/{dlg.database}")
        QMessageBox.information(self, "База данных", "Подключение выполнено.")

    def _on_db_search(self) -> None:
        dlg = DbSearchDialog(self)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return
        results = self._db.search(dlg.query)
        self._log(f"БД: поиск '{dlg.query}', найдено {len(results)}")
        QMessageBox.information(
            self,
            "База данных",
            "Поиск выполнен.\n"
            f"Запрос: {dlg.query}\n"
            f"Результатов: {len(results)}",
        )

    def _on_db_delete(self) -> None:
        dlg = DbDeleteDialog(self)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return
        ok = self._db.delete(dlg.record_id)
        if ok:
            self._log(f"БД: удаление ID={dlg.record_id}")
            QMessageBox.information(self, "База данных", f"Удаление выполнено.\nID: {dlg.record_id}")
        else:
            QMessageBox.warning(self, "База данных", "Удаление не выполнено.")

    def _on_about(self) -> None:
        AboutDialog(self).exec()

    # --- Helpers ---

    def _log(self, message: str) -> None:
        if hasattr(self, "_log_view") and self._log_view is not None:
            self._log_view.append(message)

    def _refresh_title(self) -> None:
        if self._state.project is None:
            self.setWindowTitle("Подсистема формирования эскизов")
            return
        dirty = "*" if self._state.is_dirty else ""
        self.setWindowTitle(f"{dirty}{self._state.project.name} — Подсистема эскизов")

    def _refresh_project_panel(self) -> None:
        if not hasattr(self, "_project_name_lbl"):
            return
        if self._state.project is None:
            self._project_name_lbl.setText("—")
            self._project_file_lbl.setText("—")
            self._image_lbl.setText("—")
            self._calib_lbl.setText("—")
            self._canny_lbl.setText("—")
            self._contours_lbl.setText("—")
            self._sketch_lbl.setText("—")
            return

        self._project_name_lbl.setText(self._state.project.name)
        self._project_file_lbl.setText(str(self._state.project.project_file))
        self._image_lbl.setText(self._state.image_path.name if self._state.image_path else "—")
        self._calib_lbl.setText(
            f"{self._state.calibration.real_distance:g} {self._state.calibration.units}"
            if self._state.calibration
            else "—"
        )
        self._canny_lbl.setText(
            f"{self._state.canny_params.low_threshold}/{self._state.canny_params.high_threshold}"
            if self._state.canny_params
            else "—"
        )
        self._contours_lbl.setText("есть" if self._state.contours else "нет")
        if isinstance(self._state.sketch, dict) and isinstance(self._state.sketch.get("entities"), list):
            self._sketch_lbl.setText(f"есть ({len(self._state.sketch['entities'])})")
        else:
            self._sketch_lbl.setText("нет")

    def _refresh_image_status(self) -> None:
        if self._state.image_path is None:
            self._status_img.setText("Изображение: —")
            return
        w, h = self._workspace.image_size()
        self._status_img.setText(f"Изображение: {w}×{h}")

    def _on_zoom_changed(self, z: float) -> None:
        self._status_zoom.setText(f"Масштаб: {int(z * 100)}%")

    def _on_mouse_pos_changed(self, p) -> None:
        self._status_pos.setText(f"X: {p.x():.0f}  Y: {p.y():.0f}")

    def _maybe_handle_unsaved(self) -> bool:
        if self._state.project is None or not self._state.is_dirty:
            return True
        answer = QMessageBox.question(
            self,
            "Несохранённые изменения",
            "Есть несохранённые изменения. Сохранить проект?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Yes,
        )
        if answer == QMessageBox.StandardButton.Cancel:
            return False
        if answer == QMessageBox.StandardButton.No:
            return True
        # Yes
        self._on_project_save()
        return not self._state.is_dirty

    def _show_error(self, title: str, message: str) -> None:
        QMessageBox.critical(self, title, message)
        self.statusBar().showMessage(title)

    def _show_warning(self, title: str, message: str) -> None:
        QMessageBox.warning(self, title, message)
        self.statusBar().showMessage(title)

