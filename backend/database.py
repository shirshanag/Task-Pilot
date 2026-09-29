from dotenv import load_dotenv
load_dotenv()

import sqlite3
from pathlib import Path


# Project root directory
BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = BASE_DIR / "my_task.db"


def db_run(query, params=(), fetch=False):
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    try:
        cur = conn.execute(query, params)

        rows = (
            [dict(r) for r in cur.fetchall()]
            if fetch
            else None
        )

        conn.commit()

        return rows if fetch else cur.lastrowid

    finally:
        conn.close()


def init_db():

    # ----------------------------------------------------------
    # Users
    # ----------------------------------------------------------

    db_run("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # ----------------------------------------------------------
    # Tasks
    # ----------------------------------------------------------

    db_run("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            task_no INTEGER,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT CHECK (
                status IN (
                    'pending',
                    'in_progress',
                    'completed'
                )
            ) DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)

    # ----------------------------------------------------------
    # Migration for old tasks table
    # ----------------------------------------------------------

    cols = [
        c["name"]
        for c in db_run(
            "PRAGMA table_info(tasks)",
            fetch=True
        )
    ]

    if "user_id" not in cols:
        db_run(
            "ALTER TABLE tasks ADD COLUMN user_id INTEGER"
        )

    if "task_no" not in cols:
        db_run(
            "ALTER TABLE tasks ADD COLUMN task_no INTEGER"
        )

    # ----------------------------------------------------------
    # Backfill task numbers
    # ----------------------------------------------------------

    db_run("""
        UPDATE tasks
        SET task_no = (
            SELECT COUNT(*)
            FROM tasks t2
            WHERE t2.user_id = tasks.user_id
            AND t2.id <= tasks.id
        )
        WHERE task_no IS NULL
        AND user_id IS NOT NULL;
    """)

    # ----------------------------------------------------------
    # Unique task number per user
    # ----------------------------------------------------------

    db_run("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_tasks_user_taskno
        ON tasks(user_id, task_no);
    """)

    # ----------------------------------------------------------
    # Automatically assign task number
    # ----------------------------------------------------------

    db_run("""
        CREATE TRIGGER IF NOT EXISTS trg_tasks_assign_task_no
        AFTER INSERT ON tasks
        WHEN NEW.task_no IS NULL
        AND NEW.user_id IS NOT NULL
        BEGIN

            UPDATE tasks
            SET task_no = (
                SELECT COALESCE(MAX(task_no), 0) + 1
                FROM tasks
                WHERE user_id = NEW.user_id
            )
            WHERE id = NEW.id;

        END;
    """)

    # ----------------------------------------------------------
    # Chat history
    # ----------------------------------------------------------

    db_run("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)


# Initialize database
init_db()