"""Работа с базой данных SQLite (один файл bookings.db рядом с ботом)."""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).with_name("bookings.db")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS bookings (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL,
                name       TEXT    NOT NULL,
                phone      TEXT    NOT NULL,
                service    TEXT    NOT NULL,
                date       TEXT    NOT NULL,   -- YYYY-MM-DD
                time       TEXT    NOT NULL,   -- HH:MM
                created_at TEXT    DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        # Один слот (дата + время) может быть занят только одной записью
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS uniq_slot ON bookings(date, time)"
        )
        # Миграция: флаг «напоминание отправлено» (для баз, созданных раньше)
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(bookings)")}
        if "reminded" not in cols:
            conn.execute("ALTER TABLE bookings ADD COLUMN reminded INTEGER DEFAULT 0")
        # Дни, закрытые владельцем (отпуск, праздники)
        conn.execute("CREATE TABLE IF NOT EXISTS closed_days (date TEXT PRIMARY KEY)")


def busy_times(date: str) -> set[str]:
    with _connect() as conn:
        rows = conn.execute("SELECT time FROM bookings WHERE date = ?", (date,))
        return {r["time"] for r in rows}


def add_booking(user_id: int, name: str, phone: str, service: str,
                date: str, time: str) -> int | None:
    """Возвращает id записи или None, если слот уже кто-то занял."""
    try:
        with _connect() as conn:
            cur = conn.execute(
                "INSERT INTO bookings (user_id, name, phone, service, date, time) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, name, phone, service, date, time),
            )
            return cur.lastrowid
    except sqlite3.IntegrityError:
        return None


def user_bookings(user_id: int, from_date: str) -> list[sqlite3.Row]:
    with _connect() as conn:
        return conn.execute(
            "SELECT * FROM bookings WHERE user_id = ? AND date >= ? "
            "ORDER BY date, time",
            (user_id, from_date),
        ).fetchall()


def upcoming_bookings(from_date: str) -> list[sqlite3.Row]:
    with _connect() as conn:
        return conn.execute(
            "SELECT * FROM bookings WHERE date >= ? ORDER BY date, time",
            (from_date,),
        ).fetchall()


def get_booking(booking_id: int) -> sqlite3.Row | None:
    with _connect() as conn:
        return conn.execute(
            "SELECT * FROM bookings WHERE id = ?", (booking_id,)
        ).fetchone()


def due_reminders(now: str, until: str) -> list[sqlite3.Row]:
    """Записи без напоминания, которые начнутся в интервале (now, until]. Формат 'YYYY-MM-DD HH:MM'."""
    with _connect() as conn:
        return conn.execute(
            "SELECT * FROM bookings WHERE reminded = 0 "
            "AND date || ' ' || time > ? AND date || ' ' || time <= ?",
            (now, until),
        ).fetchall()


def mark_reminded(booking_id: int) -> None:
    with _connect() as conn:
        conn.execute("UPDATE bookings SET reminded = 1 WHERE id = ?", (booking_id,))


def close_day(day: str) -> None:
    with _connect() as conn:
        conn.execute("INSERT OR IGNORE INTO closed_days (date) VALUES (?)", (day,))


def open_day(day: str) -> bool:
    with _connect() as conn:
        return conn.execute("DELETE FROM closed_days WHERE date = ?", (day,)).rowcount > 0


def closed_days(from_date: str) -> list[str]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT date FROM closed_days WHERE date >= ? ORDER BY date", (from_date,)
        )
        return [r["date"] for r in rows]


def bookings_on(day: str) -> list[sqlite3.Row]:
    with _connect() as conn:
        return conn.execute(
            "SELECT * FROM bookings WHERE date = ? ORDER BY time", (day,)
        ).fetchall()


def delete_booking(booking_id: int, user_id: int) -> bool:
    with _connect() as conn:
        cur = conn.execute(
            "DELETE FROM bookings WHERE id = ? AND user_id = ?",
            (booking_id, user_id),
        )
        return cur.rowcount > 0
