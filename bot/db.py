import json
import sqlite3
from datetime import datetime, timedelta, UTC


class Database:
    def __init__(self, path: str = "kapsula.db") -> None:
        self.path = path

    def connect(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def init(self):
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    tg_user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    phone TEXT,
                    source TEXT,
                    campaign TEXT,
                    name_hint TEXT,
                    fsm_state TEXT,
                    answers TEXT DEFAULT '{}',
                    sent_content_ids TEXT DEFAULT '[]',
                    followups_sent INTEGER DEFAULT 0,
                    followup_at TEXT,
                    created_at TEXT,
                    updated_at TEXT
                );
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tg_user_id INTEGER,
                    stage TEXT,
                    event TEXT,
                    payload TEXT,
                    created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS leads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tg_user_id INTEGER,
                    summary TEXT,
                    score INTEGER,
                    temperature TEXT,
                    next_step TEXT,
                    preferred_time TEXT,
                    created_at TEXT
                );
                """
            )

    def upsert_user(self, tg_user_id: int, **fields):
        now = datetime.now(UTC).isoformat()
        with self.connect() as conn:
            row = conn.execute("SELECT tg_user_id FROM users WHERE tg_user_id=?", (tg_user_id,)).fetchone()
            if row:
                sets = ", ".join([f"{k}=?" for k in fields]) + ", updated_at=?"
                vals = list(fields.values()) + [now, tg_user_id]
                conn.execute(f"UPDATE users SET {sets} WHERE tg_user_id=?", vals)
            else:
                base = {
                    "username": None,
                    "phone": None,
                    "source": None,
                    "campaign": None,
                    "name_hint": None,
                    "fsm_state": "WELCOME",
                    "answers": "{}",
                    "sent_content_ids": "[]",
                    "followups_sent": 0,
                    "followup_at": None,
                    "created_at": now,
                    "updated_at": now,
                }
                base.update(fields)
                cols = ",".join(["tg_user_id"] + list(base.keys()))
                q = ",".join(["?"] * (len(base) + 1))
                conn.execute(f"INSERT INTO users ({cols}) VALUES ({q})", [tg_user_id] + list(base.values()))

    def get_user(self, tg_user_id: int):
        with self.connect() as conn:
            return conn.execute("SELECT * FROM users WHERE tg_user_id=?", (tg_user_id,)).fetchone()

    def save_answers(self, tg_user_id: int, updates: dict):
        user = self.get_user(tg_user_id)
        answers = json.loads(user["answers"] or "{}")
        answers.update(updates)
        self.upsert_user(tg_user_id, answers=json.dumps(answers, ensure_ascii=False))

    def set_followup(self, tg_user_id: int, hours: int):
        dt = (datetime.now(UTC) + timedelta(hours=hours)).isoformat()
        user = self.get_user(tg_user_id)
        sent = user["followups_sent"] if user else 0
        self.upsert_user(tg_user_id, followup_at=dt, followups_sent=sent)

    def log_session(self, tg_user_id: int, stage: str, event: str, payload: str = ""):
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO sessions (tg_user_id, stage, event, payload, created_at) VALUES (?, ?, ?, ?, ?)",
                (tg_user_id, stage, event, payload, datetime.now(UTC).isoformat()),
            )

    def create_lead(self, tg_user_id: int, summary: str, score: int, temperature: str, next_step: str, preferred_time: str):
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO leads (tg_user_id, summary, score, temperature, next_step, preferred_time, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (tg_user_id, summary, score, temperature, next_step, preferred_time, datetime.now(UTC).isoformat()),
            )
