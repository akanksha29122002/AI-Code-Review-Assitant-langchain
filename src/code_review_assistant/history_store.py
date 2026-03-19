from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from src.code_review_assistant.config import settings
from src.code_review_assistant.models import ReviewHistoryRecord, ReviewResult


class ReviewHistoryStore:
    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = Path(db_path or settings.review_history_db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def save_review(
        self,
        *,
        source: str,
        title: str,
        result: ReviewResult,
        repository: str | None = None,
        pull_request_number: int | None = None,
        dedupe_key: str | None = None,
        raw_input: str | None = None,
    ) -> int | None:
        with sqlite3.connect(self.db_path) as conn:
            if dedupe_key:
                existing = conn.execute(
                    "SELECT id FROM review_history WHERE dedupe_key = ?",
                    (dedupe_key,),
                ).fetchone()
                if existing:
                    return None
            cursor = conn.execute(
                """
                INSERT INTO review_history (
                    source,
                    title,
                    repository,
                    pull_request_number,
                    dedupe_key,
                    overall_risk,
                    summary,
                    findings_count,
                    missing_tests_count,
                    raw_input,
                    result_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    source,
                    title,
                    repository,
                    pull_request_number,
                    dedupe_key,
                    result.overall_risk,
                    result.summary,
                    len(result.findings),
                    len(result.missing_tests),
                    raw_input,
                    json.dumps(result.model_dump(), ensure_ascii=True),
                ),
            )
            conn.commit()
            return int(cursor.lastrowid)

    def list_recent_reviews(self, limit: int = 20) -> list[ReviewHistoryRecord]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT
                    id,
                    source,
                    title,
                    repository,
                    pull_request_number,
                    overall_risk,
                    summary,
                    findings_count,
                    missing_tests_count,
                    created_at
                FROM review_history
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [ReviewHistoryRecord(**dict(row)) for row in rows]

    def mark_delivery_processed(self, delivery_id: str) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            existing = conn.execute(
                "SELECT delivery_id FROM processed_deliveries WHERE delivery_id = ?",
                (delivery_id,),
            ).fetchone()
            if existing:
                return False
            conn.execute(
                "INSERT INTO processed_deliveries (delivery_id) VALUES (?)",
                (delivery_id,),
            )
            conn.commit()
            return True

    def _initialize(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS review_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT NOT NULL,
                    title TEXT NOT NULL,
                    repository TEXT,
                    pull_request_number INTEGER,
                    dedupe_key TEXT UNIQUE,
                    overall_risk TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    findings_count INTEGER NOT NULL,
                    missing_tests_count INTEGER NOT NULL,
                    raw_input TEXT,
                    result_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS processed_deliveries (
                    delivery_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.commit()
