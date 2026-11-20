"""SQLite persistence for the Mini-CRM Demo (fictional leads only)."""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta

import pandas as pd

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.db")

LEAD_COLUMNS = [
    "id", "created_at", "company", "contact_role", "email", "industry",
    "bucket_weight_kg", "gripper_weight_kg", "payload_total", "line_rate_bpm",
    "side_selection", "shifts", "county", "hub", "verdict", "score", "payback",
    "params_json",
]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    company TEXT NOT NULL,
    contact_role TEXT NOT NULL,
    email TEXT NOT NULL,
    industry TEXT NOT NULL,
    bucket_weight_kg REAL NOT NULL,
    gripper_weight_kg REAL NOT NULL,
    payload_total REAL NOT NULL,
    line_rate_bpm REAL NOT NULL,
    side_selection TEXT NOT NULL,
    shifts INTEGER NOT NULL,
    county TEXT NOT NULL,
    hub TEXT NOT NULL,
    verdict TEXT NOT NULL,
    score INTEGER NOT NULL,
    payback TEXT NOT NULL,
    params_json TEXT NOT NULL
)
"""


def _connect() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)


def _seed_rows() -> list[dict]:
    now = datetime.now()
    return [
        {
            "created_at": (now - timedelta(days=6, hours=3)).strftime("%Y-%m-%d %H:%M"),
            "company": "Lactate Demo Carpați SRL",
            "contact_role": "Director Producție",
            "email": "productie@lactate-demo.exemplu-fictiv.ro",
            "industry": "Alimentară (găleți plastic)",
            "bucket_weight_kg": 13.0, "gripper_weight_kg": 2.8, "payload_total": 15.8,
            "line_rate_bpm": 6.5, "side_selection": "Dual", "shifts": 2,
            "county": "Ilfov", "hub": "Dragomirești-Deal",
            "verdict": "Verde", "score": 100, "payback": "24–32 luni",
            "params_json": json.dumps({"content_type": "Pastă-vâscos", "has_handle": True, "air_supply": "Da",
                                       "pallet": "Preset 13 kg (44 găleți, 4 straturi)", "seed": True}, ensure_ascii=False),
        },
        {
            "created_at": (now - timedelta(days=3, hours=1)).strftime("%Y-%m-%d %H:%M"),
            "company": "Vopsele Test Someș SRL",
            "contact_role": "Inginer Automatist",
            "email": "automatizari@vopsele-test.exemplu-fictiv.ro",
            "industry": "Non-alimentară",
            "bucket_weight_kg": 10.0, "gripper_weight_kg": 2.8, "payload_total": 12.8,
            "line_rate_bpm": 7.2, "side_selection": "Stânga", "shifts": 2,
            "county": "Cluj", "hub": "Timișoara",
            "verdict": "Galben", "score": 71, "payback": "24–32 luni",
            "params_json": json.dumps({"content_type": "Lichid", "has_handle": True, "air_supply": "Nu știu",
                                       "confidential_fields": ["Nume companie"], "seed": True}, ensure_ascii=False),
        },
        {
            "created_at": (now - timedelta(days=1, hours=5)).strftime("%Y-%m-%d %H:%M"),
            "company": "Patiserie Fictivă Moldova SRL",
            "contact_role": "Manager Mentenanță",
            "email": "mentenanta@patiserie.exemplu-fictiv.ro",
            "industry": "Alimentară (găleți plastic)",
            "bucket_weight_kg": 18.5, "gripper_weight_kg": 2.8, "payload_total": 21.3,
            "line_rate_bpm": 9.2, "side_selection": "Dreapta", "shifts": 3,
            "county": "Iași", "hub": "Iași",
            "verdict": "Roșu", "score": 17, "payback": "18–24 luni",
            "params_json": json.dumps({"content_type": "Pastă-vâscos", "has_handle": True, "air_supply": "Nu",
                                       "seed": True}, ensure_ascii=False),
        },
    ]


def init_db() -> None:
    """Create tables and seed 3 fictional demo leads if the table is empty."""
    with closing(_connect()) as conn:
        conn.execute(_SCHEMA)
        count = conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
        if count == 0:
            _insert_many(conn, _seed_rows())
        conn.commit()


def _insert_many(conn: sqlite3.Connection, rows: list[dict]) -> None:
    cols = [c for c in LEAD_COLUMNS if c != "id"]
    placeholders = ", ".join("?" for _ in cols)
    conn.executemany(
        f"INSERT INTO leads ({', '.join(cols)}) VALUES ({placeholders})",
        [tuple(row[c] for c in cols) for row in rows],
    )


def insert_lead(row: dict) -> int:
    """Insert a lead; returns the new row id."""
    row = dict(row)
    row.setdefault("created_at", datetime.now().strftime("%Y-%m-%d %H:%M"))
    cols = [c for c in LEAD_COLUMNS if c != "id"]
    with closing(_connect()) as conn:
        cur = conn.execute(
            f"INSERT INTO leads ({', '.join(cols)}) VALUES ({', '.join('?' for _ in cols)})",
            tuple(row[c] for c in cols),
        )
        conn.commit()
        return int(cur.lastrowid)


def get_leads() -> pd.DataFrame:
    with closing(_connect()) as conn:
        return pd.read_sql_query("SELECT * FROM leads ORDER BY datetime(created_at) DESC, id DESC", conn)


def delete_lead(lead_id: int) -> bool:
    with closing(_connect()) as conn:
        cur = conn.execute("DELETE FROM leads WHERE id = ?", (int(lead_id),))
        conn.commit()
        return cur.rowcount > 0


def reset_demo_data() -> None:
    """Delete all leads and restore the 3 fictional seed leads."""
    with closing(_connect()) as conn:
        conn.execute(_SCHEMA)
        conn.execute("DELETE FROM leads")
        _insert_many(conn, _seed_rows())
        conn.commit()
