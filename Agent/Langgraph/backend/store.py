from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime
from threading import Lock
from typing import Any, Dict, Iterable, List, Optional

from .config import settings


DB_PATH = os.path.abspath(settings.db_path)
_LOCK = Lock()


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {row["name"] for row in rows}


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, ddl: str) -> None:
    if column not in _columns(conn, table):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")


def init_db() -> None:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS budget (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                total_budget REAL NOT NULL,
                spent REAL NOT NULL,
                remaining REAL NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt TEXT NOT NULL,
                response TEXT,
                risk_score REAL NOT NULL,
                complexity TEXT NOT NULL,
                complexity_score REAL NOT NULL,
                complexity_tags TEXT NOT NULL,
                estimated_tokens INTEGER NOT NULL,
                actual_tokens INTEGER NOT NULL,
                estimated_cost REAL NOT NULL,
                actual_cost REAL NOT NULL,
                selected_model TEXT,
                routing_scores TEXT NOT NULL,
                confidence REAL NOT NULL,
                routing_reason TEXT,
                latency_ms REAL NOT NULL,
                cache_hit INTEGER NOT NULL,
                blocked INTEGER NOT NULL,
                timeline TEXT NOT NULL,
                timestamp TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS blocked_attacks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt TEXT NOT NULL,
                reason TEXT,
                risk_score REAL NOT NULL,
                matched_patterns TEXT NOT NULL,
                user_id TEXT,
                session_id TEXT,
                prompt_hash TEXT,
                attack_type TEXT,
                severity TEXT,
                safe_rewrite TEXT,
                timestamp TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS model_metrics (
                model_name TEXT PRIMARY KEY,
                total_requests INTEGER NOT NULL,
                total_cost REAL NOT NULL,
                total_tokens INTEGER NOT NULL,
                avg_latency_ms REAL NOT NULL,
                avg_confidence REAL NOT NULL,
                last_used TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS cache_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt TEXT NOT NULL,
                response TEXT NOT NULL,
                model_id TEXT,
                model_label TEXT,
                similarity REAL NOT NULL,
                cost_saved REAL NOT NULL,
                hits INTEGER NOT NULL,
                timestamp TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS session_memory (
                session_id TEXT PRIMARY KEY,
                summary TEXT NOT NULL,
                turns INTEGER NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )

        for table, column, ddl in [
            ("requests", "user_id", "TEXT DEFAULT 'anonymous'"),
            ("requests", "session_id", "TEXT DEFAULT 'default'"),
            ("requests", "prompt_hash", "TEXT"),
            ("requests", "selected_model_id", "TEXT"),
            ("requests", "selected_model_label", "TEXT"),
            ("requests", "selected_tier", "TEXT"),
            ("requests", "prompt_tokens", "INTEGER DEFAULT 0"),
            ("requests", "completion_tokens", "INTEGER DEFAULT 0"),
            ("requests", "total_tokens", "INTEGER DEFAULT 0"),
            ("requests", "execution_time_ms", "REAL DEFAULT 0"),
            ("requests", "security_result", "TEXT"),
            ("requests", "escalation_history", "TEXT"),
            ("requests", "quality_score", "REAL DEFAULT 0"),
            ("requests", "quality_label", "TEXT"),
            ("requests", "verification_status", "TEXT"),
            ("requests", "verification_notes", "TEXT"),
            ("requests", "self_eval", "TEXT"),
            ("requests", "prompt_hash", "TEXT"),
            ("blocked_attacks", "user_id", "TEXT"),
            ("blocked_attacks", "session_id", "TEXT"),
            ("blocked_attacks", "prompt_hash", "TEXT"),
            ("blocked_attacks", "attack_type", "TEXT"),
            ("blocked_attacks", "severity", "TEXT"),
            ("blocked_attacks", "safe_rewrite", "TEXT"),
        ]:
            _ensure_column(conn, table, column, ddl)

        row = conn.execute("SELECT id FROM budget WHERE id = 1").fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO budget (id, total_budget, spent, remaining, updated_at) VALUES (1, ?, 0, ?, ?)",
                (settings.total_budget, settings.total_budget, datetime.utcnow().isoformat()),
            )
        conn.commit()


def get_budget() -> Dict[str, Any]:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM budget WHERE id = 1").fetchone()
        if row is None:
            return {"total": settings.total_budget, "spent": 0.0, "remaining": settings.total_budget, "pct_spent": 0.0}
        pct = (row["spent"] / row["total_budget"]) if row["total_budget"] else 0.0
        return {
            "total": row["total_budget"],
            "spent": row["spent"],
            "remaining": row["remaining"],
            "pct_spent": round(pct, 4),
            "warning": pct >= settings.budget_warning_threshold,
            "exhausted": row["remaining"] <= 0,
        }


def reset_budget(new_total: float) -> Dict[str, Any]:
    with _LOCK:
        with _connect() as conn:
            conn.execute(
                "UPDATE budget SET total_budget = ?, spent = 0, remaining = ?, updated_at = ? WHERE id = 1",
                (new_total, new_total, datetime.utcnow().isoformat()),
            )
            conn.commit()
    return get_budget()


def deduct_budget(amount: float) -> Dict[str, Any]:
    with _LOCK:
        with _connect() as conn:
            budget = conn.execute("SELECT * FROM budget WHERE id = 1").fetchone()
            if budget is not None:
                spent = budget["spent"] + amount
                remaining = budget["remaining"] - amount
                conn.execute(
                    "UPDATE budget SET spent = ?, remaining = ?, updated_at = ? WHERE id = 1",
                    (spent, remaining, datetime.utcnow().isoformat()),
                )
                conn.commit()
    return get_budget()


def create_request(data: Dict[str, Any]) -> int:
    payload = dict(data)
    payload["complexity_tags"] = json.dumps(payload.get("complexity_tags", []))
    payload["routing_scores"] = json.dumps(payload.get("routing_scores", {}))
    payload["timeline"] = json.dumps(payload.get("timeline", []))
    payload["escalation_history"] = json.dumps(payload.get("escalation_history", []))
    payload["verification_notes"] = json.dumps(payload.get("verification_notes", []))
    payload["self_eval"] = json.dumps(payload.get("self_eval", {}))
    payload["cache_hit"] = int(bool(payload.get("cache_hit", False)))
    payload["blocked"] = int(bool(payload.get("blocked", False)))
    payload["prompt_tokens"] = int(payload.get("prompt_tokens", 0))
    payload["completion_tokens"] = int(payload.get("completion_tokens", 0))
    payload["total_tokens"] = int(payload.get("total_tokens", 0))
    payload["timestamp"] = datetime.utcnow().isoformat()

    with _connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO requests (
                prompt, response, risk_score, complexity, complexity_score, complexity_tags,
                estimated_tokens, actual_tokens, estimated_cost, actual_cost, selected_model,
                routing_scores, confidence, routing_reason, latency_ms, cache_hit, blocked, timeline, timestamp,
                user_id, session_id, prompt_hash, selected_model_id, selected_model_label, selected_tier,
                prompt_tokens, completion_tokens, total_tokens, execution_time_ms, security_result, escalation_history,
                quality_score, quality_label, verification_status, verification_notes, self_eval
            ) VALUES (
                :prompt, :response, :risk_score, :complexity, :complexity_score, :complexity_tags,
                :estimated_tokens, :actual_tokens, :estimated_cost, :actual_cost, :selected_model,
                :routing_scores, :confidence, :routing_reason, :latency_ms, :cache_hit, :blocked, :timeline, :timestamp
                , :user_id, :session_id, :prompt_hash, :selected_model_id, :selected_model_label, :selected_tier
                , :prompt_tokens, :completion_tokens, :total_tokens, :execution_time_ms, :security_result, :escalation_history
                , :quality_score, :quality_label, :verification_status, :verification_notes, :self_eval
            )
            """,
            payload,
        )
        conn.commit()
        return int(cursor.lastrowid)


def log_attack(data: Dict[str, Any]) -> None:
    payload = {
        "prompt": data.get("prompt", ""),
        "reason": data.get("reason", ""),
        "risk_score": data.get("risk_score", 0.0),
        "matched_patterns": json.dumps(data.get("matched_patterns", [])),
        "user_id": data.get("user_id", "anonymous"),
        "session_id": data.get("session_id", "default"),
        "prompt_hash": data.get("prompt_hash", ""),
        "attack_type": data.get("attack_type", "unknown"),
        "severity": data.get("severity", "low"),
        "safe_rewrite": data.get("safe_rewrite", ""),
        "timestamp": datetime.utcnow().isoformat(),
    }
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO blocked_attacks (
                prompt, reason, risk_score, matched_patterns, user_id, session_id, prompt_hash,
                attack_type, severity, safe_rewrite, timestamp
            ) VALUES (
                :prompt, :reason, :risk_score, :matched_patterns, :user_id, :session_id, :prompt_hash,
                :attack_type, :severity, :safe_rewrite, :timestamp
            )
            """,
            payload,
        )
        conn.commit()


def update_model_metrics(model_name: str, cost: float, tokens: int, latency_ms: float, confidence: float) -> None:
    with _LOCK:
        with _connect() as conn:
            row = conn.execute("SELECT * FROM model_metrics WHERE model_name = ?", (model_name,)).fetchone()
            if row is None:
                conn.execute(
                    """
                    INSERT INTO model_metrics (model_name, total_requests, total_cost, total_tokens, avg_latency_ms, avg_confidence, last_used)
                    VALUES (?, 1, ?, ?, ?, ?, ?)
                    """,
                    (model_name, cost, tokens, latency_ms, confidence, datetime.utcnow().isoformat()),
                )
            else:
                n = row["total_requests"]
                conn.execute(
                    """
                    UPDATE model_metrics
                    SET total_requests = ?, total_cost = ?, total_tokens = ?, avg_latency_ms = ?, avg_confidence = ?, last_used = ?
                    WHERE model_name = ?
                    """,
                    (
                        n + 1,
                        row["total_cost"] + cost,
                        row["total_tokens"] + tokens,
                        (row["avg_latency_ms"] * n + latency_ms) / (n + 1),
                        (row["avg_confidence"] * n + confidence) / (n + 1),
                        datetime.utcnow().isoformat(),
                        model_name,
                    ),
                )
            conn.commit()


def create_cache_entry(prompt: str, response: str, model_id: str, model_label: str, similarity: float, cost_saved: float) -> int:
    with _LOCK:
        with _connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO cache_entries (prompt, response, model_id, model_label, similarity, cost_saved, hits, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, 1, ?)
                """,
                (prompt, response, model_id, model_label, similarity, cost_saved, datetime.utcnow().isoformat()),
            )
            conn.commit()
            return int(cursor.lastrowid)


def increment_cache_hit(entry_id: int) -> None:
    with _LOCK:
        with _connect() as conn:
            conn.execute("UPDATE cache_entries SET hits = hits + 1 WHERE id = ?", (entry_id,))
            conn.commit()


def get_cache_entries(limit: int = 100) -> List[Dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM cache_entries ORDER BY timestamp DESC LIMIT ?", (limit,)).fetchall()
    return [dict(row) for row in rows]


def get_cache_stats() -> Dict[str, Any]:
    with _connect() as conn:
        total = conn.execute("SELECT COUNT(*) AS value FROM cache_entries").fetchone()["value"]
        hits = conn.execute("SELECT COUNT(*) AS value FROM cache_entries WHERE hits > 1").fetchone()["value"]
        cost_saved = conn.execute("SELECT COALESCE(SUM(cost_saved), 0) AS value FROM cache_entries").fetchone()["value"]
    return {"total_entries": total, "cache_hits": hits, "total_cost_saved": cost_saved}


def get_recent_requests(limit: int = 50) -> List[Dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM requests ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [_decode_request(row) for row in rows]


def get_session_requests(session_id: str, limit: int = 12) -> List[Dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM requests WHERE session_id = ? ORDER BY id DESC LIMIT ?",
            (session_id, limit),
        ).fetchall()
    return [_decode_request(row) for row in rows]


def get_recent_attacks(limit: int = 20) -> List[Dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM blocked_attacks ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    attacks: List[Dict[str, Any]] = []
    for row in rows:
        attacks.append(
            {
                "id": row["id"],
                "prompt": row["prompt"],
                "reason": row["reason"],
                "risk_score": row["risk_score"],
                "matched_patterns": json.loads(row["matched_patterns"]),
                "timestamp": row["timestamp"],
            }
        )
    return attacks


def get_model_metrics() -> List[Dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM model_metrics ORDER BY total_requests DESC").fetchall()
    return [dict(row) for row in rows]


def get_stats() -> Dict[str, Any]:
    with _connect() as conn:
        total = conn.execute("SELECT COUNT(*) AS value FROM requests").fetchone()["value"]
        cost = conn.execute("SELECT COALESCE(SUM(actual_cost), 0) AS value FROM requests").fetchone()["value"]
        tokens = conn.execute("SELECT COALESCE(SUM(actual_tokens), 0) AS value FROM requests").fetchone()["value"]
        blocked = conn.execute("SELECT COUNT(*) AS value FROM requests WHERE blocked = 1").fetchone()["value"]
        cache_hits = conn.execute("SELECT COUNT(*) AS value FROM requests WHERE cache_hit = 1").fetchone()["value"]
        cost_saved = conn.execute("SELECT COALESCE(SUM(cost_saved), 0) AS value FROM cache_entries").fetchone()["value"]
        avg_confidence = conn.execute("SELECT COALESCE(AVG(confidence), 0) AS value FROM requests").fetchone()["value"]
        avg_latency = conn.execute("SELECT COALESCE(AVG(latency_ms), 0) AS value FROM requests").fetchone()["value"]
        escalations = conn.execute("SELECT COUNT(*) AS value FROM requests WHERE escalation_history IS NOT NULL AND escalation_history != '[]'").fetchone()["value"]
    return {
        "total_requests": total,
        "total_cost": cost,
        "total_tokens": tokens,
        "blocked": blocked,
        "cache_hits": cache_hits,
        "cost_saved": cost_saved,
        "avg_confidence": round(avg_confidence, 4),
        "avg_latency_ms": round(avg_latency, 2),
        "escalation_count": escalations,
    }


def get_analytics() -> Dict[str, Any]:
    stats = get_stats()
    with _connect() as conn:
        success = conn.execute("SELECT COUNT(*) AS value FROM requests WHERE blocked = 0").fetchone()["value"]
        active_users = conn.execute(
            "SELECT COUNT(DISTINCT user_id) AS value FROM requests WHERE timestamp >= datetime('now', '-15 minutes')"
        ).fetchone()["value"]
        model_rows = conn.execute(
            "SELECT COALESCE(selected_model_label, selected_model, 'Unknown') AS model_name, COUNT(*) AS value FROM requests GROUP BY model_name"
        ).fetchall()
        failure_rate = 0.0 if stats["total_requests"] == 0 else round(stats["blocked"] / stats["total_requests"], 4)
        cache_hit_ratio = 0.0 if stats["total_requests"] == 0 else round(stats["cache_hits"] / stats["total_requests"], 4)
    return {
        "totals": {
            "total_queries": stats["total_requests"],
            "successful_queries": success,
            "blocked_queries": stats["blocked"],
            "average_response_time_ms": stats["avg_latency_ms"],
            "average_confidence": stats["avg_confidence"],
            "cache_hit_ratio": cache_hit_ratio,
            "escalation_count": stats["escalation_count"],
        },
        "model_usage": [{"model": row["model_name"], "count": row["value"]} for row in model_rows],
        "token_consumption": stats["total_tokens"],
        "failure_rate": failure_rate,
        "active_users": active_users,
    }


def get_health() -> Dict[str, Any]:
    stats = get_stats()
    with _connect() as conn:
        latency = conn.execute("SELECT COALESCE(AVG(latency_ms), 0) AS value FROM requests WHERE timestamp >= datetime('now', '-30 minutes')").fetchone()["value"]
        failure_rate = 0.0 if stats["total_requests"] == 0 else stats["blocked"] / stats["total_requests"]
        active_users = conn.execute(
            "SELECT COUNT(DISTINCT user_id) AS value FROM requests WHERE timestamp >= datetime('now', '-15 minutes')"
        ).fetchone()["value"]
    latency_state = "green" if latency < 1000 else "yellow" if latency < 3000 else "red"
    failure_state = "green" if failure_rate < 0.1 else "yellow" if failure_rate < 0.25 else "red"
    return {
        "api_latency_ms": round(latency, 2),
        "average_response_time_ms": stats["avg_latency_ms"],
        "failure_rate": round(failure_rate, 4),
        "active_users": active_users,
        "model_availability": "green" if stats["blocked"] < stats["total_requests"] else "yellow",
        "indicators": {
            "latency": latency_state,
            "failure": failure_state,
            "models": "green",
        },
    }


def _decode_request(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "prompt": row["prompt"],
        "response": row["response"],
        "risk_score": row["risk_score"],
        "complexity": row["complexity"],
        "complexity_score": row["complexity_score"],
        "complexity_tags": json.loads(row["complexity_tags"]),
        "estimated_tokens": row["estimated_tokens"],
        "actual_tokens": row["actual_tokens"],
        "estimated_cost": row["estimated_cost"],
        "actual_cost": row["actual_cost"],
        "selected_model": row["selected_model"],
        # Alias so the frontend's `selected_model_label` reference resolves correctly
        "selected_model_label": row["selected_model"],
        "selected_model_id": row["selected_model_id"] if "selected_model_id" in row.keys() else row["selected_model"],
        "selected_tier": row["selected_tier"] if "selected_tier" in row.keys() else "",
        "routing_scores": json.loads(row["routing_scores"]),
        "confidence": row["confidence"],
        "routing_reason": row["routing_reason"],
        "latency_ms": row["latency_ms"],
        "cache_hit": bool(row["cache_hit"]),
        "blocked": bool(row["blocked"]),
        "timeline": json.loads(row["timeline"]),
        "user_id": row["user_id"] if "user_id" in row.keys() else "anonymous",
        "session_id": row["session_id"] if "session_id" in row.keys() else "default",
        "prompt_hash": row["prompt_hash"] if "prompt_hash" in row.keys() else "",
        "security_result": row["security_result"] if "security_result" in row.keys() else "",
        "escalation_history": json.loads(row["escalation_history"]) if "escalation_history" in row.keys() and row["escalation_history"] else [],
        "prompt_tokens": row["prompt_tokens"] if "prompt_tokens" in row.keys() else 0,
        "completion_tokens": row["completion_tokens"] if "completion_tokens" in row.keys() else 0,
        "total_tokens": row["total_tokens"] if "total_tokens" in row.keys() else row["actual_tokens"],
        "execution_time_ms": row["execution_time_ms"] if "execution_time_ms" in row.keys() else row["latency_ms"],
        "quality_score": row["quality_score"] if "quality_score" in row.keys() else 0,
        "quality_label": row["quality_label"] if "quality_label" in row.keys() else "",
        "verification_status": row["verification_status"] if "verification_status" in row.keys() else "",
        "verification_notes": json.loads(row["verification_notes"]) if "verification_notes" in row.keys() and row["verification_notes"] else [],
        "self_eval": json.loads(row["self_eval"]) if "self_eval" in row.keys() and row["self_eval"] else {},
        "timestamp": row["timestamp"],
    }


def set_session_memory(session_id: str, summary: str, turns: int) -> Dict[str, Any]:
    with _LOCK:
        with _connect() as conn:
            conn.execute(
                """
                INSERT INTO session_memory (session_id, summary, turns, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET summary = excluded.summary, turns = excluded.turns, updated_at = excluded.updated_at
                """,
                (session_id, summary, turns, datetime.utcnow().isoformat()),
            )
            conn.commit()
    return get_session_memory(session_id)


def get_session_memory(session_id: str) -> Dict[str, Any]:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM session_memory WHERE session_id = ?", (session_id,)).fetchone()
    if row is None:
        return {"session_id": session_id, "summary": "", "turns": 0, "updated_at": None}
    return dict(row)
