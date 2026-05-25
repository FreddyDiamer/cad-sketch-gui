"""Операции с базой данных подсистемы (SQLite).

Хранит историю обработанных изображений: путь к исходному файлу,
параметры калибровки, путь к экспортированному DXF и использованные
параметры обработки. Это обеспечивает воспроизводимость результата
и возможность повторного построения эскиза с теми же настройками.

Имена таблиц намеренно заданы на русском языке — в соответствии с
требованиями ТЗ к локализации программы. SQLite допускает Unicode
в именах таблиц без дополнительной настройки.

Схема БД:
    пользователь            — пользователи системы (опционально);
    изображение             — обработанные изображения;
    параметры_калибровки    — калибровка для каждого изображения;
    эскиз                   — экспортированные DXF-файлы;
    параметры_обработки     — настройки Canny и аппроксимации.

Между таблицами настроены связи FOREIGN KEY с каскадным удалением
(ON DELETE CASCADE): удаление изображения автоматически удаляет
связанные калибровки, эскизы и параметры обработки.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from core.models import Calibration, CannyParams


# Скрипт инициализации схемы. Выполняется при каждом подключении
# (CREATE IF NOT EXISTS — идемпотентен).
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
    """Обёртка над SQLite-соединением: подключение, CRUD-операции."""

    def __init__(self) -> None:
        # Соединение создаётся лениво в connect(); до этого — None.
        self._conn: sqlite3.Connection | None = None
        self._db_path: Path | None = None

    @property
    def is_connected(self) -> bool:
        return self._conn is not None

    def connect(self, db_path: str) -> None:
        """Подключение к файлу SQLite. Файл создаётся, если его нет."""
        path = Path(db_path.strip() or "sketch_db.sqlite")
        path.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(str(path))
        # Удобный доступ к колонкам по имени (row["path"] вместо row[1]).
        conn.row_factory = sqlite3.Row
        # Каскадное удаление работает только если включить FK явно.
        conn.execute("PRAGMA foreign_keys = ON")
        # Создаём таблицы, если их ещё нет.
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
        """Сохраняет в БД полную запись об обработке: изображение →
        калибровка → эскиз (DXF) → параметры обработки.

        Возвращает id созданной записи в таблице `изображение`.
        Все вставки в одной транзакции — целостность гарантируется.
        """
        if self._conn is None:
            raise RuntimeError("Нет подключения к базе данных.")

        # Единая метка времени для всех связанных записей.
        now = datetime.now().isoformat(sep=" ", timespec="seconds")
        cur = self._conn.cursor()

        # 1) Запись об изображении (родительская запись).
        cur.execute(
            "INSERT INTO изображение(user_id, path, date) VALUES (NULL, ?, ?)",
            (str(image_path), now),
        )
        image_id = cur.lastrowid

        # 2) Параметры калибровки для этого изображения.
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

        # 3) Запись об эскизе (путь к экспортированному DXF).
        cur.execute(
            "INSERT INTO эскиз(image_id, dxf_path, date) VALUES (?, ?, ?)",
            (image_id, str(dxf_path), now),
        )
        sketch_id = cur.lastrowid

        # 4) Параметры обработки (Canny + аппроксимация) для этого эскиза.
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

        # Фиксируем транзакцию: все четыре вставки атомарны.
        self._conn.commit()
        return str(image_id)

    def search(self, query: str) -> list[dict]:
        """Поиск по подстроке в пути к изображению (LIKE %query%)."""
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
        """Удаление записи об изображении по id.

        Благодаря ON DELETE CASCADE одновременно удаляются связанные
        калибровки, эскизы и параметры обработки.
        """
        if self._conn is None or not record_id.strip():
            return False
        try:
            rid = int(record_id.strip())
        except ValueError:
            # Пользователь ввёл не число — считаем, что записи нет.
            return False
        cur = self._conn.cursor()
        cur.execute("DELETE FROM изображение WHERE id = ?", (rid,))
        self._conn.commit()
        return cur.rowcount > 0

    def close(self) -> None:
        """Закрытие соединения (вызывается при завершении работы)."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None
            self._db_path = None
