"""SQLite storage for sessions and hands."""
import sqlite3
import time
from pathlib import Path

DB = Path(__file__).resolve().parent.parent / "poker.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions(
  id INTEGER PRIMARY KEY, start_ts REAL, end_ts REAL,
  balance_before REAL, buy_in REAL, bb REAL, balance_after REAL);
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
    return con


def start_session(con, balance_before, buy_in, bb):
    cur = con.execute("INSERT INTO sessions(start_ts,balance_before,buy_in,bb) VALUES(?,?,?,?)",
                      (time.time(), balance_before, buy_in, bb))
    con.commit()
    return cur.lastrowid


def end_session(con, sid, balance_after):
    con.execute("UPDATE sessions SET end_ts=?, balance_after=? WHERE id=?",
                (time.time(), balance_after, sid))
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
