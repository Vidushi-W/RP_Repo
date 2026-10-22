"""SQLite fallback/cache for the MongoDB-first Component 3 attempt flow."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE = ROOT / "data" / "attempts.sqlite3"


class AttemptStore:
    """Persist attempt documents locally when MongoDB is unreachable.

    Successful MongoDB writes are also cached locally, so later offline
    sessions still have the learner's recent history for remediation.
    """

    def __init__(self, database_path: str | Path = DEFAULT_DATABASE) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS user_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    sign_id TEXT NOT NULL,
                    similarity_score REAL,
                    dtw_distance REAL,
                    detected_errors TEXT NOT NULL,
                    joint_deviations TEXT NOT NULL,
                    sampled_frames INTEGER NOT NULL,
                    analysis_latency_ms REAL,
                    feedback_message TEXT,
                    document_json TEXT
                )
                """
            )
            columns = {row["name"] for row in connection.execute("PRAGMA table_info(user_attempts)")}
            migrations = {
                "analysis_latency_ms": "REAL",
                "document_json": "TEXT",
            }
            for name, sql_type in migrations.items():
                if name not in columns:
                    connection.execute(f"ALTER TABLE user_attempts ADD COLUMN {name} {sql_type}")
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_attempts_user_time "
                "ON user_attempts(user_id, timestamp DESC)"
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=5.0)
        connection.row_factory = sqlite3.Row
        return connection

    def record(self, document: dict) -> dict:
        """Cache one MongoDB-shaped attempt and return its local copy."""
        attempt = dict(document)
        attempt.setdefault(
            "timestamp",
            datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        )
        metrics = attempt.get("metrics", {})
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO user_attempts (
                    user_id, timestamp, sign_id, similarity_score, dtw_distance,
                    detected_errors, joint_deviations, sampled_frames,
                    analysis_latency_ms, feedback_message, document_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    attempt["user_id"], attempt["timestamp"], attempt["sign_id"],
                    metrics.get("similarity_score"), metrics.get("dtw_distance"),
                    json.dumps(attempt.get("detected_error_codes", [])),
                    json.dumps(attempt.get("finger_angles", {})),
                    int(metrics.get("sampled_frames", 0)),
                    metrics.get("analysis_latency_ms"),
                    attempt.get("feedback_message"),
                    json.dumps(attempt, allow_nan=False),
                ),
            )
            row = connection.execute(
                "SELECT id FROM user_attempts WHERE id = ?", (cursor.lastrowid,)
            ).fetchone()
        attempt["local_id"] = row["id"]
        return attempt

    def recent(self, user_id: str, limit: int = 5) -> list[dict]:
        """Read the newest cached MongoDB-shaped attempts for one learner."""
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM user_attempts WHERE user_id = ? "
                "ORDER BY timestamp DESC, id DESC LIMIT ?",
                (user_id, limit),
            ).fetchall()
        attempts = []
        for row in rows:
            if row["document_json"]:
                attempt = json.loads(row["document_json"])
            else:
                # Convert pre-schema local attempts so old feedback remains
                # available for recurring-error analysis after this upgrade.
                attempt = {
                    "user_id": row["user_id"],
                    "sign_id": row["sign_id"],
                    "timestamp": row["timestamp"],
                    "detected_error_codes": json.loads(row["detected_errors"]),
                    "status": "COMPLETED" if row["similarity_score"] is not None else "INSUFFICIENT_DATA",
                    "metrics": {
                        "similarity_score": row["similarity_score"],
                        "dtw_distance": row["dtw_distance"],
                        "analysis_latency_ms": row["analysis_latency_ms"],
                    },
                }
            attempt["local_id"] = row["id"]
            attempts.append(attempt)
        return attempts
