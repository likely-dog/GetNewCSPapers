import sqlite3
from pathlib import Path
from typing import Iterable, Optional
from datetime import datetime
from ..models import Paper
import json


DB_PATH = Path("getnewcspapers_data.db")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS papers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT,
            external_id TEXT UNIQUE,
            title TEXT,
            authors TEXT,
            abstract TEXT,
            primary_category TEXT,
            categories TEXT,
            link TEXT,
            published TEXT,
            updated TEXT,
            comment TEXT,
            direction TEXT,
            direction_scores TEXT,
            summary TEXT,
            method_improvement TEXT,
            experiments TEXT,
            venue_name TEXT,
            venue_year TEXT,
            venue_status TEXT,
            venue_ccf_level TEXT,
            match_confidence REAL,
            pushed INTEGER DEFAULT 0
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS preferences (
            id INTEGER PRIMARY KEY CHECK (id=1),
            areas TEXT,
            push_time TEXT,
            max_per_day INTEGER,
            interval_days INTEGER DEFAULT 1,
            last_push_date TEXT
        )
        """
    )
    # 自动迁移：为已有 preferences 表补充缺失列
    try:
        cur.execute("PRAGMA table_info(preferences)")
        cols = [row[1] for row in cur.fetchall()]
        if "interval_days" not in cols:
            cur.execute("ALTER TABLE preferences ADD COLUMN interval_days INTEGER DEFAULT 1")
        if "last_push_date" not in cols:
            cur.execute("ALTER TABLE preferences ADD COLUMN last_push_date TEXT")
    except Exception:
        pass
    try:
        cur.execute("PRAGMA table_info(users)")
        cols = [row[1] for row in cur.fetchall()]
        if "push_time_user" not in cols:
            cur.execute("ALTER TABLE users ADD COLUMN push_time_user TEXT")
        if "max_per_day_user" not in cols:
            cur.execute("ALTER TABLE users ADD COLUMN max_per_day_user INTEGER")
    except Exception:
        pass
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            password_hash TEXT,
            role TEXT,
            interests TEXT,
            push_time_user TEXT,
            max_per_day_user INTEGER
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS user_pushed (
            user_id INTEGER,
            external_id TEXT,
            pushed_at TEXT,
            PRIMARY KEY (user_id, external_id)
        )
        """
    )
    conn.commit()
    conn.close()


def save_preferences(areas: Iterable[str], push_time: str = "08:00", max_per_day: int = 10, interval_days: int = 1, last_push_date: Optional[str] = None):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "REPLACE INTO preferences (id, areas, push_time, max_per_day, interval_days, last_push_date) VALUES (1, ?, ?, ?, ?, ?)",
        (json.dumps(list(areas), ensure_ascii=False), push_time, max_per_day, interval_days, last_push_date),
    )
    conn.commit()
    conn.close()


def get_preferences():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT areas, push_time, max_per_day, interval_days, last_push_date FROM preferences WHERE id=1")
    row = cur.fetchone()
    conn.close()
    if not row:
        return [], "08:00", 10, 1, None
    areas = json.loads(row[0])
    return areas, row[1], int(row[2]), int(row[3]) if row[3] is not None else 1, row[4]


def upsert_paper(p: Paper):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT OR REPLACE INTO papers
        (source, external_id, title, authors, abstract, primary_category, categories, link, published, updated, comment,
         direction, direction_scores, summary, method_improvement, experiments, venue_name, venue_year, venue_status,
         venue_ccf_level, match_confidence)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            p.source,
            p.external_id,
            p.title,
            json.dumps(p.authors, ensure_ascii=False),
            p.abstract,
            p.primary_category,
            json.dumps(p.categories, ensure_ascii=False),
            p.link,
            p.published.isoformat() if p.published else None,
            p.updated.isoformat() if p.updated else None,
            p.comment,
            p.direction,
            json.dumps(p.direction_scores, ensure_ascii=False),
            p.summary,
            p.method_improvement,
            p.experiments,
            p.venue_name,
            p.venue_year,
            p.venue_status,
            p.venue_ccf_level,
            p.match_confidence if p.match_confidence is not None else None,
        ),
    )
    conn.commit()
    conn.close()


def query_unpushed_by_areas(areas, limit=10):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT * FROM papers WHERE pushed=0")
    rows = cur.fetchall()
    conn.close()
    results = []
    for r in rows:
        direction = r[12]
        if not direction or direction not in areas:
            continue
        results.append(r)
    return results[:limit]


def mark_papers_pushed(external_ids: Iterable[str]):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    for eid in external_ids:
        cur.execute("UPDATE papers SET pushed=1 WHERE external_id=?", (eid,))
    conn.commit()
    conn.close()


def create_admin_if_missing():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE email=?", ("admin",))
    row = cur.fetchone()
    if not row:
        cur.execute("INSERT INTO users (email, password_hash, role, interests) VALUES (?, ?, ?, ?)", ("admin", "", "admin", json.dumps([], ensure_ascii=False)))
    conn.commit()
    conn.close()


def create_user(email: str, password_hash: str, interests: Iterable[str], role: str = "user"):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO users (email, password_hash, role, interests) VALUES (?, ?, ?, ?)", (email, password_hash, role, json.dumps(list(interests), ensure_ascii=False)))
    conn.commit()
    conn.close()


def get_user_by_email(email: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id, email, password_hash, role, interests, push_time_user, max_per_day_user FROM users WHERE email=?", (email,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {"id": row[0], "email": row[1], "password_hash": row[2], "role": row[3], "interests": json.loads(row[4]) if row[4] else [], "push_time_user": row[5], "max_per_day_user": row[6]}

def list_users():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id, email, password_hash, role, interests, push_time_user, max_per_day_user FROM users")
    rows = cur.fetchall()
    conn.close()
    res = []
    for r in rows:
        res.append({"id": r[0], "email": r[1], "password_hash": r[2], "role": r[3], "interests": json.loads(r[4]) if r[4] else [], "push_time_user": r[5], "max_per_day_user": r[6]})
    return res

def set_user_settings(user_id: int, push_time: str, max_per_day: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE users SET push_time_user=?, max_per_day_user=? WHERE id=?", (push_time, int(max_per_day), user_id))
    conn.commit()
    conn.close()

def query_candidates_by_direction(direction: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT external_id, title, authors, abstract, link, direction, venue_ccf_level, published FROM papers WHERE direction=?", (direction,))
    rows = cur.fetchall()
    conn.close()
    results = []
    for r in rows:
        results.append({
            "external_id": r[0],
            "title": r[1],
            "authors": json.loads(r[2]),
            "abstract": r[3],
            "link": r[4],
            "direction": r[5],
            "venue_ccf_level": r[6],
            "published": r[7]
        })
    return results


def mark_user_pushed(user_id: int, external_ids: Iterable[str]):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    now = datetime.utcnow().isoformat()
    for eid in external_ids:
        cur.execute("INSERT OR REPLACE INTO user_pushed (user_id, external_id, pushed_at) VALUES (?, ?, ?)", (user_id, eid, now))
    conn.commit()
    conn.close()


def query_user_candidates(user_areas: Iterable[str]):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT external_id, title, authors, abstract, link, direction, venue_ccf_level, published FROM papers WHERE direction IS NOT NULL")
    rows = cur.fetchall()
    conn.close()
    results = []
    for r in rows:
        direction = r[5]
        if direction in user_areas:
            results.append({
                "external_id": r[0],
                "title": r[1],
                "authors": json.loads(r[2]),
                "abstract": r[3],
                "link": r[4],
                "direction": r[5],
                "venue_ccf_level": r[6],
                "published": r[7]
            })
    return results
