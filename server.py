"""Poker study app (PLAY-MONEY only, manual entry). Run: python3 server.py"""
import threading
import webbrowser

from flask import Flask, jsonify, request, send_from_directory

from pokercalc import analytics, coach, service, store
from pokercalc.parser import Query

app = Flask(__name__, static_folder="static", static_url_path="/static")


def db():
    return store.connect()


@app.get("/")
def index():
    return send_from_directory("static", "index.html")


@app.post("/api/calc")
def calc():
    d = request.get_json()
    if len(d["hole"]) != 2 or len(d["board"]) not in (0, 3, 4, 5):
        return jsonify(error="need 2 hole cards and 0/3/4/5 board cards"), 400
    return jsonify(service.evaluate(d))


@app.get("/api/session")
def session():
    con = db()
    row = store.open_session(con)
    last = con.execute("SELECT balance_after FROM sessions WHERE balance_after IS NOT NULL "
                       "ORDER BY id DESC LIMIT 1").fetchone()
    return jsonify(active=dict(row) if row else None, last_balance=last[0] if last else None)


@app.post("/api/session/start")
def session_start():
    d = request.get_json()
    sid = store.start_session(db(), float(d["balance"]), float(d["buy_in"]), float(d["bb"]),
                              float(d.get("deposit") or 0))
    return jsonify(id=sid)


@app.post("/api/session/end")
def session_end():
    con = db()
    row = store.open_session(con)
    if row:
        d = request.get_json()
        store.end_session(con, row["id"], float(d["balance_after"]), float(d.get("deposit") or 0))
    return jsonify(ok=True)


@app.post("/api/hand")
def hand():
    d = request.get_json()
    con = db()
    row = store.open_session(con)
    q = Query(d["hole"], d["board"], float(d.get("pot") or 0), float(d.get("call") or 0),
              int(d.get("opps") or 1), d.get("range_pct") or None)
    res = d.get("result")
    store.log_hand(con, row["id"] if row else None, q, d.get("position"),
                   float(d["stack"]) if d.get("stack") else None, d["equity"], d["required"],
                   d.get("suggested"), d.get("taken"), float(res) if res not in (None, "") else None)
    return jsonify(ok=True)


@app.post("/api/history/clear")
def history_clear():
    store.clear_history(db())
    return jsonify(ok=True)


@app.post("/api/coach")
def coach_api():
    con = db()
    if not con.execute("SELECT 1 FROM hands LIMIT 1").fetchone():
        return jsonify(ok=False, text="Save a few hands first - the coach needs something to look at."), 400
    ok, text = coach.run_coach(coach.build_prompt(con))
    return jsonify(ok=ok, text=text), (200 if ok else 502)


@app.get("/api/analytics")
def analytics_api():
    return jsonify(analytics.summary(db()))


if __name__ == "__main__":
    url = "http://127.0.0.1:5173"
    threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    app.run(host="127.0.0.1", port=5173, threaded=True)
