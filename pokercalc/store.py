"""SQLite storage for sessions and hands."""
import sqlite3
import time
from pathlib import Path

DB = Path(__file__).resolve().parent.parent / "poker.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions(
  id INTEGER PRIMARY KEY, start_ts REAL, end_ts REAL,
  balance_before REAL, buy_in REAL, bb REAL, balance_after REAL,
  deposit_before REAL DEFAULT 0, deposit_during REAL DEFAULT 0);
CREATE TABLE IF NOT EXISTS hands(
  id INTEGER PRIMARY KEY, session_id INTEGER, ts REAL,
  hole TEXT, board TEXT, pot REAL, call REAL, opps INTEGER, range_pct INTEGER,
  position TEXT, stack REAL, equity REAL, required REAL,
  suggested TEXT, taken TEXT, result REAL);
"""


def connect(path=DB):
    con = sqlite3.connect(str(path))
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    cols = {r[1] for r in con.execute("PRAGMA table_info(sessions)")}
    for c in ("deposit_before", "deposit_during"):  # upgrade older databases
        if c not in cols:
            con.execute(f"ALTER TABLE sessions ADD COLUMN {c} REAL DEFAULT 0")
    con.commit()
    return con


def start_session(con, balance_before, buy_in, bb, deposit_before=0.0):
    """balance_before already includes any top-up; deposit_before says how much of it was a deposit."""
    cur = con.execute("INSERT INTO sessions(start_ts,balance_before,buy_in,bb,deposit_before) VALUES(?,?,?,?,?)",
                      (time.time(), balance_before, buy_in, bb, deposit_before))
    con.commit()
    return cur.lastrowid


def end_session(con, sid, balance_after, deposit_during=0.0):
    con.execute("UPDATE sessions SET end_ts=?, balance_after=?, deposit_during=? WHERE id=?",
                (time.time(), balance_after, deposit_during, sid))
    con.commit()


def open_session(con):
    return con.execute("SELECT * FROM sessions WHERE end_ts IS NULL ORDER BY id DESC LIMIT 1").fetchone()


def log_hand(con, sid, q, position, stack, eq, required, suggested, taken, result):
    con.execute(
        "INSERT INTO hands(session_id,ts,hole,board,pot,call,opps,range_pct,position,stack,"
        "equity,required,suggested,taken,result) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (sid, time.time(), " ".join(q.hole), " ".join(q.board), q.pot, q.call, q.opponents,
         q.range_pct, position, stack, eq, required, suggested, taken, result))
    con.commit()


def clear_history(con):
    """Permanently delete every saved session and hand."""
    con.execute("DELETE FROM hands")
    con.execute("DELETE FROM sessions")
    con.commit()
