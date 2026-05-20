from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from core.models import Calibration, CannyParams


_SCHEMA = """
CREATE TABLE IF NOT EXISTS пользователь (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT
);
CREATE TABLE IF NOT EXISTS изображение (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    path TEXT,
    date TEXT,
    FOREIGN KEY(user_id) REFERENCES пользователь(id) ON DELETE SET NULL
);
CREATE TABLE IF NOT EXISTS параметры_калибровки (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    image_id INTEGER UNIQUE,
    x1 INTEGER,
    y1 INTEGER,
    x2 INTEGER,
    y2 INTEGER,
    real_distance REAL,
    units TEXT,
    FOREIGN KEY(image_id) REFERENCES изображение(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS эскиз (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    image_id INTEGER,
    dxf_path TEXT,
    date TEXT,
    FOREIGN KEY(image_id) REFERENCES изображение(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS параметры_обработки (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sketch_id INTEGER,
    canny_min INTEGER,
    canny_max INTEGER,
    dp_epsilon REAL,
    gauss_kernel INTEGER,
    FOREIGN KEY(sketch_id) REFERENCES эскиз(id) ON DELETE CASCADE
);
"""


class DatabaseOperations:
    """Операции с SQLite-БД эскизов."""

    def __init__(self) -> None:
        self._conn: sqlite3.Connection | None = None
        self._db_path: Path | None = None

    @property
    def is_connected(self) -> bool:
        return self._conn is not None

    def connect(self, host: str, db: str, user: str, password: str) -> None:
        # SQLite: host/user/password игнорируются, db — путь к файлу.
        path = Path(db.strip() or "sketch_db.sqlite")
        path.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(str(path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(_SCHEMA)
        conn.commit()

        self._conn = conn
        self._db_path = path

    def save_image_record(
        self,
        image_path: Path,
        calibration: Calibration,
        canny: CannyParams,
        dxf_path: Path,
    ) -> str:
        if self._conn is None:
            raise RuntimeError("Нет подключения к базе данных.")

        now = datetime.now().isoformat(sep=" ", timespec="seconds")
        cur = self._conn.cursor()

        cur.execute(
            "INSERT INTO изображение(user_id, path, date) VALUES (NULL, ?, ?)",
            (str(image_path), now),
        )
        image_id = cur.lastrowid

        cur.execute(
            "INSERT INTO параметры_калибровки(image_id, x1, y1, x2, y2, real_distance, units) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                image_id,
                int(calibration.x1),
                int(calibration.y1),
                int(calibration.x2),
                int(calibration.y2),
                float(calibration.real_distance),
                str(calibration.units),
            ),
        )

        cur.execute(
            "INSERT INTO эскиз(image_id, dxf_path, date) VALUES (?, ?, ?)",
            (image_id, str(dxf_path), now),
        )
        sketch_id = cur.lastrowid

        cur.execute(
            "INSERT INTO параметры_обработки(sketch_id, canny_min, canny_max, dp_epsilon, gauss_kernel) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                sketch_id,
                int(canny.low_threshold),
                int(canny.high_threshold),
                float(canny.dp_epsilon),
                int(canny.gauss_kernel),
            ),
        )

        self._conn.commit()
        return str(image_id)

    def search(self, query: str) -> list[dict]:
        if self._conn is None or not query.strip():
            return []
        cur = self._conn.cursor()
        cur.execute(
            "SELECT id, path, date FROM изображение WHERE path LIKE ? ORDER BY id DESC",
            (f"%{query.strip()}%",),
        )
        return [
            {"id": str(row["id"]), "path": row["path"], "date": row["date"]}
            for row in cur.fetchall()
        ]

    def delete(self, record_id: str) -> bool:
        if self._conn is None or not record_id.strip():
            return False
        try:
            rid = int(record_id.strip())
        except ValueError:
            return False
        cur = self._conn.cursor()
        cur.execute("DELETE FROM изображение WHERE id = ?", (rid,))
        self._conn.commit()
        return cur.rowcount > 0

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None
            self._db_path = None
