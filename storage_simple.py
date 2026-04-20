"""
storage_simple.py
SQLite Storage Module for Review Analysis Prototype.
Schema: users, products, reviews, analysis_results
"""
import sqlite3
import os
from werkzeug.security import generate_password_hash

DB_PATH = os.getenv("DB_PATH", "reviews.db")


class DB:
    def __init__(self):
        self.db_path = DB_PATH

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def init_tables(self):
        conn = self._connect()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                email    TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                full_name TEXT NOT NULL DEFAULT '',
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS products (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                name     TEXT NOT NULL UNIQUE,
                category TEXT NOT NULL DEFAULT '',
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS reviews (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id    INTEGER NOT NULL,
                customer_name TEXT DEFAULT 'Аноним',
                review_text   TEXT NOT NULL,
                status        TEXT DEFAULT 'pending',
                created_at    TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (product_id) REFERENCES products(id)
            );

            CREATE TABLE IF NOT EXISTS analysis_results (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                review_id INTEGER UNIQUE NOT NULL,
                sentiment TEXT,
                summary   TEXT,
                aspects   TEXT DEFAULT '[]',
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (review_id) REFERENCES reviews(id)
            );
        """)
        conn.commit()
        conn.close()
        print("✓ Таблицы инициализированы")

    def init_test_user(self):
        conn = self._connect()
        existing = conn.execute(
            "SELECT id FROM users WHERE email = ?", ("Ivanov@mail.ru",)
        ).fetchone()
        if not existing:
            hashed = generate_password_hash("user")
            conn.execute(
                "INSERT INTO users (email, password, full_name) VALUES (?, ?, ?)",
                ("Ivanov@mail.ru", hashed, "Test User"),
            )
            conn.commit()
            print("✓ Тестовый пользователь создан (login: Ivanov@mail.ru  password: user)")
        conn.close()

    def exec(self, query: str, params=None) -> int:
        """Execute INSERT/UPDATE/DELETE, return lastrowid."""
        conn = self._connect()
        cur = conn.execute(query, params or ())
        conn.commit()
        last_id = cur.lastrowid
        conn.close()
        return last_id

    def query(self, query: str, params=None) -> list[dict]:
        """Execute SELECT, return list of dicts."""
        conn = self._connect()
        rows = conn.execute(query, params or ()).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def query_one(self, query: str, params=None) -> dict | None:
        """Execute SELECT, return single dict or None."""
        conn = self._connect()
        row = conn.execute(query, params or ()).fetchone()
        conn.close()
        return dict(row) if row else None


db = DB()