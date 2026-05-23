from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import ezdxf

from core.models import Calibration, CannyParams, Circle, Polyline, Project, ProjectState


class FileOperations:
    """Операции с файлами проекта."""

    @staticmethod
    def save_project(state: ProjectState) -> None:
        if state.project is None:
            raise ValueError("Нет проекта для сохранения.")

        data = {
            "name": state.project.name,
            "image_path": str(state.image_path) if state.image_path else None,
            "calibration": asdict(state.calibration) if state.calibration else None,
            "canny_params": asdict(state.canny_params) if state.canny_params else None,
        }
        state.project.project_file.parent.mkdir(parents=True, exist_ok=True)
        state.project.project_file.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    @staticmethod
    def load_project(project_file: Path) -> Project:
        raw = project_file.read_text(encoding="utf-8")
        data = json.loads(raw)
        name = str(data.get("name") or "").strip()
        if not name:
            raise ValueError("Некорректный файл проекта: отсутствует имя.")
        return Project(name=name, project_file=project_file)

    @staticmethod
    def load_project_state(project_file: Path) -> ProjectState:
        """Полное восстановление состояния проекта из JSON."""
        data = json.loads(project_file.read_text(encoding="utf-8"))
        name = str(data.get("name") or "").strip()
        if not name:
            raise ValueError("Некорректный файл проекта: отсутствует имя.")

        project = Project(name=name, project_file=project_file)
        image_path = Path(data["image_path"]) if data.get("image_path") else None

        calibration: Calibration | None = None
        if data.get("calibration"):
            c = data["calibration"]
            calibration = Calibration(
                real_distance=float(c.get("real_distance", 100.0)),
                units=str(c.get("units", "мм")),
                x1=int(c.get("x1", 0)),
                y1=int(c.get("y1", 0)),
                x2=int(c.get("x2", 0)),
                y2=int(c.get("y2", 0)),
            )

        canny_params: CannyParams | None = None
        if data.get("canny_params"):
            cp = data["canny_params"]
            canny_params = CannyParams(
                low_threshold=int(cp.get("low_threshold", 50)),
                high_threshold=int(cp.get("high_threshold", 150)),
                gauss_kernel=int(cp.get("gauss_kernel", 5)),
                dp_epsilon=float(cp.get("dp_epsilon", 2.0)),
            )

        return ProjectState(
            project=project,
            image_path=image_path,
            calibration=calibration,
            canny_params=canny_params,
            contours=None,
            sketch=None,
            is_dirty=False,
        )

    @staticmethod
    def export_dxf_placeholder(
        target_file: Path,
        polylines: list[Polyline | Circle],
        project: Project,
        calibration: Calibration,
        canny_params: CannyParams,
    ) -> None:
        """Экспорт эскиза в DXF (LWPOLYLINE + CIRCLE, слой SKETCH, единицы мм)."""
        if target_file.suffix.lower() != ".dxf":
            raise ValueError("Файл экспорта должен иметь расширение .dxf")
        target_file.parent.mkdir(parents=True, exist_ok=True)

        doc = ezdxf.new(dxfversion="R2010", setup=True)
        doc.units = ezdxf.units.MM
        if "SKETCH" not in doc.layers:
            doc.layers.add("SKETCH", color=5)
        msp = doc.modelspace()

        # Координаты эскиза в пикселях — масштабируем в миллиметры по калибровке.
        scale = calibration.scale_mm_per_pixel if calibration else 1.0
        if scale <= 0:
            scale = 1.0

        for ent in polylines:
            if isinstance(ent, Circle):
                msp.add_circle(
                    (ent.cx * scale, ent.cy * scale), ent.radius * scale,
                    dxfattribs={"layer": "SKETCH"},
                )
                continue
            if not ent.points or len(ent.points) < 2:
                continue
            closed = ent.points[0] == ent.points[-1]
            scaled_pts = [(x * scale, y * scale) for x, y in ent.points]
            msp.add_lwpolyline(
                scaled_pts,
                dxfattribs={"layer": "SKETCH", "closed": closed},
            )

        doc.saveas(str(target_file))
