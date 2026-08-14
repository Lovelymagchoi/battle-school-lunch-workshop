"""분석 결과를 저장하는 SQLite 저장소."""

from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from .schemas import AnalysisCreate, AnalysisResponse, AgentResult, SchoolSummary


SCHEMA = """
CREATE TABLE IF NOT EXISTS schools (
    school_code TEXT PRIMARY KEY,
    edu_office_code TEXT NOT NULL,
    school_name TEXT NOT NULL,
    edu_office_name TEXT NOT NULL,
    location_name TEXT NOT NULL,
    school_kind_name TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS analysis_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_date TEXT NOT NULL,
    winner TEXT NOT NULL,
    overall_summary TEXT NOT NULL,
    comparison_result TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS analysis_schools (
    analysis_id INTEGER NOT NULL REFERENCES analysis_requests(id) ON DELETE CASCADE,
    school_code TEXT NOT NULL REFERENCES schools(school_code),
    school_role TEXT NOT NULL CHECK (school_role IN ('school_a', 'school_b')),
    PRIMARY KEY (analysis_id, school_role)
);
CREATE TABLE IF NOT EXISTS agent_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id INTEGER NOT NULL REFERENCES analysis_requests(id) ON DELETE CASCADE,
    school_code TEXT NOT NULL REFERENCES schools(school_code),
    agent_name TEXT NOT NULL,
    score INTEGER NOT NULL CHECK (score BETWEEN 1 AND 5),
    analysis TEXT NOT NULL,
    evidence TEXT NOT NULL,
    UNIQUE (analysis_id, school_code, agent_name)
);
"""


class AnalysisRepository:
    """분석 저장과 조회를 하나의 SQLite 트랜잭션으로 제공한다."""

    def __init__(self, database_path: str) -> None:
        self._path = Path(database_path)
        if str(self._path) != ":memory:":
            self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path, uri=False)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def create(self, request: AnalysisCreate) -> int:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            with connection:
                cursor = connection.execute(
                    """
                    INSERT INTO analysis_requests
                        (analysis_date, winner, overall_summary, comparison_result, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        request.analysis_date.isoformat(),
                        request.winner,
                        request.overall_summary,
                        json.dumps(request.comparison_result, ensure_ascii=False),
                        now,
                    ),
                )
                analysis_id = int(cursor.lastrowid)
                for role, school in (("school_a", request.school_a), ("school_b", request.school_b)):
                    connection.execute(
                        """
                        INSERT OR REPLACE INTO schools
                            (school_code, edu_office_code, school_name, edu_office_name,
                             location_name, school_kind_name)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            school.school_code,
                            school.edu_office_code,
                            school.school_name,
                            school.edu_office_name,
                            school.location_name,
                            school.school_kind_name,
                        ),
                    )
                    connection.execute(
                        "INSERT INTO analysis_schools (analysis_id, school_code, school_role) VALUES (?, ?, ?)",
                        (analysis_id, school.school_code, role),
                    )
                for result in request.agent_results:
                    connection.execute(
                        """
                        INSERT INTO agent_results
                            (analysis_id, school_code, agent_name, score, analysis, evidence)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            analysis_id,
                            result.school_code,
                            result.agent_name,
                            result.score,
                            result.analysis,
                            json.dumps(result.evidence, ensure_ascii=False),
                        ),
                    )
        return analysis_id

    def get(self, analysis_id: int) -> AnalysisResponse | None:
        with self._connect() as connection:
            request = connection.execute(
                "SELECT * FROM analysis_requests WHERE id = ?", (analysis_id,)
            ).fetchone()
            if request is None:
                return None
            schools = connection.execute(
                """
                SELECT a.school_role, s.*
                FROM analysis_schools a JOIN schools s ON s.school_code = a.school_code
                WHERE a.analysis_id = ?
                ORDER BY a.school_role
                """,
                (analysis_id,),
            ).fetchall()
            results = connection.execute(
                "SELECT * FROM agent_results WHERE analysis_id = ? ORDER BY id",
                (analysis_id,),
            ).fetchall()

        school_by_role = {row["school_role"]: self._school(row) for row in schools}
        return AnalysisResponse(
            analysis_id=analysis_id,
            analysis_date=date.fromisoformat(request["analysis_date"]),
            school_a=school_by_role["school_a"],
            school_b=school_by_role["school_b"],
            agent_results=[
                AgentResult(
                    school_code=row["school_code"],
                    agent_name=row["agent_name"],
                    score=row["score"],
                    analysis=row["analysis"],
                    evidence=json.loads(row["evidence"]),
                )
                for row in results
            ],
            winner=request["winner"],
            overall_summary=request["overall_summary"],
            comparison_result=json.loads(request["comparison_result"]),
        )

    @staticmethod
    def _school(row: sqlite3.Row) -> SchoolSummary:
        return SchoolSummary(
            school_code=row["school_code"],
            edu_office_code=row["edu_office_code"],
            school_name=row["school_name"],
            edu_office_name=row["edu_office_name"],
            location_name=row["location_name"],
            school_kind_name=row["school_kind_name"],
        )
