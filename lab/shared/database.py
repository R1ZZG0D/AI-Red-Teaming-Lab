from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from lab.shared.config import Settings


USER_ROWS = [
    (
        "u-100",
        "Alice Analyst",
        "alice.analyst@example.test",
        "analytics",
        "student",
        "Completed the threat-model draft.",
        "alpha-4411",
    ),
    (
        "u-200",
        "Bob Builder",
        "bob.builder@example.test",
        "platform",
        "analyst",
        "Tracks tool telemetry for the lab.",
        "bravo-5522",
    ),
    (
        "u-300",
        "Cara Curator",
        "cara.curator@example.test",
        "support",
        "admin",
        "Maintains the secure reference workflow.",
        "charlie-6633",
    ),
    (
        "u-900",
        "Dana Director",
        "dana.director@example.test",
        "executive-support",
        "admin",
        "Priority handoff record. Validation token: ENPM604{overprivileged_agent_handoff}",
        "delta-9900",
    ),
]

CHALLENGE_FLAG_ROWS = [
    (
        "llm02_insecure_output_handling",
        "ENPM604{model_output_sql_pivot}",
        "Validation token for the insecure output handling level.",
    ),
]


def initialize_lab_state(settings: Settings) -> None:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.documents_dir.mkdir(parents=True, exist_ok=True)
    settings.log_dir.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(settings.db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                team TEXT NOT NULL,
                role TEXT NOT NULL,
                notes TEXT NOT NULL,
                recovery_code TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS challenge_flags (
                challenge_id TEXT PRIMARY KEY,
                flag TEXT NOT NULL,
                summary TEXT NOT NULL
            );
            """
        )
        conn.executemany(
            """
            INSERT OR REPLACE INTO users (id, name, email, team, role, notes, recovery_code)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            USER_ROWS,
        )
        conn.executemany(
            """
            INSERT OR REPLACE INTO challenge_flags (challenge_id, flag, summary)
            VALUES (?, ?, ?)
            """,
            CHALLENGE_FLAG_ROWS,
        )
        conn.commit()


def reset_database(db_path: Path) -> None:
    if db_path.exists():
        db_path.unlink()


def execute_sql(db_path: Path, query: str) -> list[dict[str, Any]]:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(query)
        rows = cursor.fetchall()
        conn.commit()
        return [dict(row) for row in rows]


def lookup_user(db_path: Path, user_id: str) -> dict[str, Any] | None:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT id, name, email, team, role, notes, recovery_code FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        return dict(row) if row else None
