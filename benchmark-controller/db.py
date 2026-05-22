import json
import os
import uuid
from typing import Any

import psycopg  # pyright: ignore[reportMissingImports]

DATABASE_URL = os.environ.get("DATABASE_URL", "")


def db_enabled() -> bool:
    return bool(DATABASE_URL)


def init_db() -> None:
    if not db_enabled():
        return

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS benchmark_runs (
                    id UUID PRIMARY KEY,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    iterations INTEGER NOT NULL,
                    message TEXT NOT NULL,
                    nodes JSONB NOT NULL,
                    total_measurements INTEGER NOT NULL
                );
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS benchmark_results (
                    id BIGSERIAL PRIMARY KEY,
                    run_id UUID NOT NULL REFERENCES benchmark_runs(id) ON DELETE CASCADE,
                    library_name TEXT NOT NULL,
                    iteration INTEGER NOT NULL,
                    encrypt_ms DOUBLE PRECISION NOT NULL,
                    decrypt_ms DOUBLE PRECISION NOT NULL,
                    total_ms DOUBLE PRECISION NOT NULL
                );
                """
            )
        conn.commit()


def save_run(
    *,
    iterations: int,
    message: str,
    nodes: list[str],
    results: list[dict[str, Any]],
) -> str | None:
    if not db_enabled():
        return None

    run_id = str(uuid.uuid4())
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO benchmark_runs (id, iterations, message, nodes, total_measurements)
                VALUES (%s, %s, %s, %s::jsonb, %s);
                """,
                (run_id, iterations, message, json.dumps(nodes), len(results)),
            )

            for row in results:
                cur.execute(
                    """
                    INSERT INTO benchmark_results (
                        run_id,
                        library_name,
                        iteration,
                        encrypt_ms,
                        decrypt_ms,
                        total_ms
                    )
                    VALUES (%s, %s, %s, %s, %s, %s);
                    """,
                    (
                        run_id,
                        row["Biblioteka"],
                        row["Iteracja"],
                        row["Encrypt_ms"],
                        row["Decrypt_ms"],
                        row["Total_ms"],
                    ),
                )

        conn.commit()

    return run_id


def list_runs(limit: int = 20, offset: int = 0) -> list[dict[str, Any]]:
    if not db_enabled():
        return []

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, created_at, iterations, message, nodes, total_measurements
                FROM benchmark_runs
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s;
                """,
                (limit, offset),
            )
            rows = cur.fetchall()

    return [
        {
            "id": str(r[0]),
            "created_at": r[1].isoformat(),
            "iterations": r[2],
            "message": r[3],
            "nodes": r[4],
            "total_measurements": r[5],
        }
        for r in rows
    ]


def get_run(run_id: str) -> dict[str, Any] | None:
    if not db_enabled():
        return None

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, created_at, iterations, message, nodes, total_measurements
                FROM benchmark_runs
                WHERE id = %s;
                """,
                (run_id,),
            )
            row = cur.fetchone()

    if not row:
        return None

    return {
        "id": str(row[0]),
        "created_at": row[1].isoformat(),
        "iterations": row[2],
        "message": row[3],
        "nodes": row[4],
        "total_measurements": row[5],
    }


def get_run_results(run_id: str) -> list[dict[str, Any]]:
    if not db_enabled():
        return []

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT library_name, iteration, encrypt_ms, decrypt_ms, total_ms
                FROM benchmark_results
                WHERE run_id = %s
                ORDER BY id ASC;
                """,
                (run_id,),
            )
            rows = cur.fetchall()

    return [
        {
            "Biblioteka": r[0],
            "Iteracja": r[1],
            "Encrypt_ms": r[2],
            "Decrypt_ms": r[3],
            "Total_ms": r[4],
        }
        for r in rows
    ]
