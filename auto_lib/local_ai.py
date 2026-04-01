"""
local_ai.py — shared Ollama client for all projects.
Drop-in replacement for paid API calls on simple/medium tasks.
All calls are logged to ~/.local_llm_usage.db for monitoring.
"""
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import requests

OLLAMA_BASE = os.environ.get("OLLAMA_BASE", "http://localhost:11434")
DEFAULT_CODE_MODEL = "qwen2.5-coder:14b"
DEFAULT_FAST_MODEL = "llama3.2:3b"

_DB_PATH = Path.home() / ".local_llm_usage.db"


def _db():
    conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS calls (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            ts               TEXT    NOT NULL,
            model            TEXT    NOT NULL,
            caller           TEXT,
            prompt_tokens    INTEGER,
            output_tokens    INTEGER,
            total_duration_ms REAL,
            error            TEXT
        )
    """)
    conn.commit()
    return conn


def _log(model: str, caller: str, data: dict, error: str = None):
    try:
        conn = _db()
        conn.execute(
            "INSERT INTO calls (ts, model, caller, prompt_tokens, output_tokens, total_duration_ms, error) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                datetime.now(timezone.utc).isoformat(),
                model,
                caller,
                data.get("prompt_eval_count"),
                data.get("eval_count"),
                round(data.get("total_duration", 0) / 1e6, 1),
                error,
            ),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


def chat(prompt: str, model: str = DEFAULT_FAST_MODEL, system: str = None,
         timeout: int = 60, caller: str = None) -> str:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    try:
        r = requests.post(
            f"{OLLAMA_BASE}/api/chat",
            json={"model": model, "messages": messages, "stream": False},
            timeout=timeout,
        )
        r.raise_for_status()
        body = r.json()
        _log(model, caller, body)
        return body["message"]["content"]
    except Exception as e:
        _log(model, caller, {}, error=str(e))
        raise


def code(prompt: str, system: str = None, timeout: int = 120, caller: str = None) -> str:
    return chat(prompt, model=DEFAULT_CODE_MODEL, system=system, timeout=timeout, caller=caller)


def is_available() -> bool:
    try:
        return requests.get(f"{OLLAMA_BASE}/", timeout=2).status_code == 200
    except Exception:
        return False


def list_models() -> list[str]:
    try:
        return [m["name"] for m in requests.get(f"{OLLAMA_BASE}/api/tags", timeout=5).json().get("models", [])]
    except Exception:
        return []


def usage_summary(days: int = 7) -> dict:
    try:
        conn = _db()
        rows = conn.execute("""
            SELECT model,
                   COUNT(*)                        AS calls,
                   SUM(prompt_tokens)              AS prompt_tokens,
                   SUM(output_tokens)              AS output_tokens,
                   ROUND(AVG(total_duration_ms))   AS avg_ms,
                   SUM(error IS NOT NULL)          AS errors
            FROM calls
            WHERE ts >= datetime('now', ?)
            GROUP BY model
            ORDER BY calls DESC
        """, (f"-{days} days",)).fetchall()
        conn.close()
        return {
            r[0]: {"calls": r[1], "prompt_tokens": r[2] or 0, "output_tokens": r[3] or 0,
                   "avg_latency_ms": r[4] or 0, "errors": r[5]}
            for r in rows
        }
    except Exception:
        return {}


def print_usage(days: int = 7):
    """Print usage summary to stdout. Run: python -m auto_lib.local_ai [days]"""
    summary = usage_summary(days=days)
    if not summary:
        print(f"No usage data for the last {days} days.")
        return
    print(f"\nLocal LLM Usage — last {days} days\n{'─' * 50}")
    for model, stats in summary.items():
        print(f"  {model}: {stats['calls']} calls, "
              f"{stats['prompt_tokens']+stats['output_tokens']} tokens, "
              f"avg {stats['avg_latency_ms']}ms, {stats['errors']} errors")


if __name__ == "__main__":
    import sys
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    print_usage(days)
