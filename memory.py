"""
memory.py — Mutant AI persistent project memory
Saves and loads: project context, user preferences, tech stack, past decisions.
Stored as JSON in .mutant_memory.json in the working directory.
"""

import json
import os
from pathlib import Path
from datetime import datetime

MEMORY_FILE = Path(".mutant_memory.json")


def _load() -> dict:
    if MEMORY_FILE.exists():
        try:
            return json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "project": {},
        "preferences": {},
        "decisions": [],
        "errors_seen": [],
        "created_at": datetime.now().isoformat(),
    }


def _save(data: dict):
    MEMORY_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def remember_project(key: str, value: str):
    """Store a project-level fact (e.g. stack, framework, goal)."""
    data = _load()
    data["project"][key] = {"value": value, "updated": datetime.now().isoformat()}
    _save(data)
    return f"Remembered: {key} = {value}"


def remember_preference(key: str, value: str):
    """Store a user coding preference."""
    data = _load()
    data["preferences"][key] = value
    _save(data)
    return f"Preference saved: {key} = {value}"


def remember_decision(decision: str):
    """Log an architectural or code decision made during the session."""
    data = _load()
    data["decisions"].append({
        "decision": decision,
        "timestamp": datetime.now().isoformat()
    })
    # Keep last 50 decisions
    data["decisions"] = data["decisions"][-50:]
    _save(data)
    return f"Decision logged: {decision}"


def remember_error(error: str, fix: str):
    """Log an error and how it was fixed."""
    data = _load()
    data["errors_seen"].append({
        "error": error[:200],
        "fix": fix[:200],
        "timestamp": datetime.now().isoformat()
    })
    data["errors_seen"] = data["errors_seen"][-30:]
    _save(data)


def get_memory_context() -> str:
    """Return full memory as a string for injection into prompts."""
    data = _load()
    lines = ["=== MUTANT AI PROJECT MEMORY ==="]

    if data.get("project"):
        lines.append("\n📦 PROJECT CONTEXT:")
        for k, v in data["project"].items():
            val = v["value"] if isinstance(v, dict) else v
            lines.append(f"  {k}: {val}")

    if data.get("preferences"):
        lines.append("\n⚙️ USER PREFERENCES:")
        for k, v in data["preferences"].items():
            lines.append(f"  {k}: {v}")

    if data.get("decisions"):
        lines.append("\n🧠 RECENT DECISIONS:")
        for d in data["decisions"][-5:]:
            lines.append(f"  - {d['decision']}")

    if data.get("errors_seen"):
        lines.append("\n🐛 KNOWN ERRORS & FIXES:")
        for e in data["errors_seen"][-3:]:
            lines.append(f"  Error: {e['error'][:80]}")
            lines.append(f"  Fix:   {e['fix'][:80]}")

    lines.append("================================")
    return "\n".join(lines)


def clear_memory():
    if MEMORY_FILE.exists():
        MEMORY_FILE.unlink()
    return "Memory cleared."
