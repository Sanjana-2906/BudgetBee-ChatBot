# budget_engine/auth.py
from __future__ import annotations
import os, csv, hashlib, time
from dataclasses import dataclass
from typing import Optional, Dict

# ---- Use absolute path to the project root ----
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
USERS_FILE = os.path.join(BASE_DIR, "assets", "users.csv")

# Session store (persistent "remember me")
SESSIONS_FILE = os.path.join(BASE_DIR, "assets", "sessions.csv")
SESSION_TTL_SECONDS = 30 * 24 * 3600  # 30 days


@dataclass
class User:
    name: str
    email: str          # always stored lowercase + trimmed
    password_hash: str  # SHA256 (demo only)
    persona: str        # "Student" or "Professional"
    created_at: float

def ensure_user_store() -> None:
    os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["name", "email", "password_hash", "persona", "created_at"])
                # sessions.csv
    if not os.path.exists(SESSIONS_FILE):
        with open(SESSIONS_FILE, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["token", "email", "expires_at"])


def _hash_pw(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def _normalize_email(email: str) -> str:
    return (email or "").strip().lower()

def _normalize_pw(pw: str) -> str:
    return (pw or "").strip()

def _load_users() -> Dict[str, User]:
    ensure_user_store()
    users: Dict[str, User] = {}
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            email_norm = _normalize_email(row["email"])
            users[email_norm] = User(
                name=row["name"].strip(),
                email=email_norm,
                password_hash=row["password_hash"],
                persona=(row["persona"] or "").strip() or "Professional",
                created_at=float(row.get("created_at", time.time())),
            )
    return users

def _save_users(users: Dict[str, User]) -> None:
    with open(USERS_FILE, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["name", "email", "password_hash", "persona", "created_at"])
        for u in users.values():
            w.writerow([u.name, u.email, u.password_hash, u.persona, u.created_at])

def email_exists(email: str) -> bool:
    return _normalize_email(email) in _load_users()

def register_user(name: str, email: str, password: str, persona: str) -> tuple[bool, str]:
    users = _load_users()
    email_norm = _normalize_email(email)
    pw_norm = _normalize_pw(password)
    if not email_norm:
        return False, "Please enter a valid email."
    if email_norm in users:
        return False, "An account with this email already exists."
    if len(pw_norm) < 6:
        return False, "Password must be at least 6 characters."

    users[email_norm] = User(
        name=(name or "").strip() or "User",
        email=email_norm,
        password_hash=_hash_pw(pw_norm),
        persona=(persona or "Professional").strip(),
        created_at=time.time(),
    )
    _save_users(users)
    return True, "Account created successfully."

def authenticate_user(email: str, password: str) -> Optional[User]:
    users = _load_users()
    email_norm = _normalize_email(email)
    pw_norm = _normalize_pw(password)
    u = users.get(email_norm)
    if not u:
        return None
    return u if u.password_hash == _hash_pw(pw_norm) else None

def get_user(email: str) -> Optional[User]:
    return _load_users().get(_normalize_email(email))

def update_user_persona(email: str, persona: str) -> None:
    users = _load_users()
    key = _normalize_email(email)
    if key in users:
        u = users[key]
        users[key] = User(u.name, u.email, u.password_hash, (persona or u.persona).strip(), u.created_at)
        _save_users(users)
import uuid

def _load_sessions() -> Dict[str, dict]:
    ensure_user_store()
    out: Dict[str, dict] = {}
    now = time.time()
    changed = False
    if os.path.exists(SESSIONS_FILE):
        with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
            r = csv.DictReader(f)
            for row in r:
                token = (row.get("token") or "").strip()
                email = _normalize_email(row.get("email") or "")
                try:
                    exp = float(row.get("expires_at", "0"))
                except:
                    exp = 0.0
                if token and email:
                    if exp > now:
                        out[token] = {"email": email, "expires_at": exp}
                    else:
                        changed = True
    if changed:
        _save_sessions(out)
    return out

def _save_sessions(sessions: Dict[str, dict]) -> None:
    with open(SESSIONS_FILE, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["token", "email", "expires_at"])
        for t, s in sessions.items():
            w.writerow([t, s["email"], s["expires_at"]])

def create_session(email: str) -> str:
    sessions = _load_sessions()
    token = uuid.uuid4().hex
    sessions[token] = {
        "email": _normalize_email(email),
        "expires_at": time.time() + SESSION_TTL_SECONDS,
    }
    _save_sessions(sessions)
    return token

def user_from_session(token: str) -> Optional[User]:
    if not token:
        return None
    sessions = _load_sessions()
    info = sessions.get(token)
    if not info:
        return None
    # If user no longer exists, revoke.
    u = get_user(info["email"])
    return u

def revoke_session(token: str) -> None:
    sessions = _load_sessions()
    if token in sessions:
        sessions.pop(token)
        _save_sessions(sessions)
