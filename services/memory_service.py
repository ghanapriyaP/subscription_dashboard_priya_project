"""
memory_service.py
-----------------
Short-term memory : in-memory dict keyed by user_id (last 10 messages per user).
Long-term memory  : UserPreference rows in SQLite (key/value store per user).
"""
from typing import List, Dict
from sqlalchemy.orm import Session
import models

# ── Short-term store (resets when server restarts) ────────────────────────────
_short_term: Dict[int, List[dict]] = {}
MAX_SHORT_TERM = 10


def get_short_term(user_id: int) -> List[dict]:
    return _short_term.get(user_id, [])


def add_to_short_term(user_id: int, role: str, content: str) -> None:
    if user_id not in _short_term:
        _short_term[user_id] = []
    _short_term[user_id].append({"role": role, "content": content})
    # Keep only the last MAX_SHORT_TERM messages
    if len(_short_term[user_id]) > MAX_SHORT_TERM:
        _short_term[user_id] = _short_term[user_id][-MAX_SHORT_TERM:]


def clear_short_term(user_id: int) -> None:
    _short_term.pop(user_id, None)


# ── Persistent message store ──────────────────────────────────────────────────

def save_message(user_id: int, role: str, content: str, db: Session) -> None:
    """Persist to DB and update in-memory short-term store."""
    msg = models.ChatMessage(user_id=user_id, role=role, content=content)
    db.add(msg)
    db.commit()
    add_to_short_term(user_id, role, content)


def get_conversation_history(user_id: int, db: Session) -> List[dict]:
    """
    Return history for the LLM context.
    Use short-term in-memory store if populated; otherwise load last 10 from DB.
    """
    if user_id in _short_term and _short_term[user_id]:
        return _short_term[user_id]
    # Cold start — load from DB
    rows = (
        db.query(models.ChatMessage)
        .filter(models.ChatMessage.user_id == user_id)
        .order_by(models.ChatMessage.created_at.desc())
        .limit(MAX_SHORT_TERM)
        .all()
    )
    history = [{"role": r.role, "content": r.content} for r in reversed(rows)]
    _short_term[user_id] = history
    return history


# ── Long-term preferences ─────────────────────────────────────────────────────

def get_preference(user_id: int, key: str, db: Session) -> str | None:
    pref = (
        db.query(models.UserPreference)
        .filter(models.UserPreference.user_id == user_id, models.UserPreference.key == key)
        .first()
    )
    return pref.value if pref else None


def set_preference(user_id: int, key: str, value: str, db: Session) -> None:
    pref = (
        db.query(models.UserPreference)
        .filter(models.UserPreference.user_id == user_id, models.UserPreference.key == key)
        .first()
    )
    if pref:
        pref.value = value
    else:
        pref = models.UserPreference(user_id=user_id, key=key, value=value)
        db.add(pref)
    db.commit()


def get_all_preferences(user_id: int, db: Session) -> Dict[str, str]:
    rows = db.query(models.UserPreference).filter(models.UserPreference.user_id == user_id).all()
    return {r.key: r.value for r in rows}
