"""Stats over logged sessions/hands. Deposits (top-ups) are never counted as winnings."""
import time

WIN_WINDOW = 20      # hands in the rolling win-rate window
CALL_WINDOW = 10     # calls in the rolling equity window
POSITIONS = ["UTG", "HJ", "CO", "BTN", "SB", "BB"]
STREETS = {0: "Preflop", 3: "Flop", 4: "Turn", 5: "River"}


def _rolling(vals, w, start=1):
    out = []
    for i in range(len(vals)):
        win = vals[max(0, i + 1 - w):i + 1]
        out.append(sum(win) / len(win) if i + 1 >= start else None)
    return out


def _label(ts):
    return time.strftime("%d %b", time.localtime(ts)) if ts else ""


def _pl(x):
    return x["balance_after"] - x["balance_before"] - (x["deposit_during"] or 0)


def summary(con):
    s = {}
    sess = con.execute("SELECT * FROM sessions ORDER BY id").fetchall()
    hands = con.execute("SELECT h.*, s.bb AS bb FROM hands h LEFT JOIN sessions s ON s.id=h.session_id "
                        "ORDER BY h.ts").fetchall()
    done = [x for x in sess if x["balance_after"] is not None]
    s["sessions"] = len(sess)
    s["hands"] = len(hands)

    # ---- balance, with deposits separated from results
    s["session_labels"] = [_label(x["end_ts"]) for x in done]
    s["session_pl"] = [_pl(x) for x in done]
    s["total_pl"] = sum(s["session_pl"])
    s["balance_labels"], s["balance_points"], s["balance_ex_deposits"], s["deposits"] = [], [], [], []
    s["total_deposits"] = 0.0
    if done:
        start = done[0]["balance_before"]
        s["balance_labels"] = ["Start"] + s["session_labels"]
        s["balance_points"] = [start] + [x["balance_after"] for x in done]
        run, ex = 0.0, [start]
        for i, x in enumerate(done):
            run += _pl(x)
            ex.append(start + run)
        s["balance_ex_deposits"] = ex
        # deposit between sessions = jump from last balance_after to this balance_before
        dep = [0.0]
        for i, x in enumerate(done):
            before = (x["deposit_before"] or 0) if i else 0
            dep.append(before + (x["deposit_during"] or 0))
        s["deposits"] = dep
        s["total_deposits"] = sum(dep)

    # ---- per-hand results and rolling win rate
    res = [h for h in hands if h["result"] is not None]
    cum, tot = [], 0.0
    for h in res:
        tot += h["result"]
        cum.append(tot)
    s["cum_results"] = cum
    s["hand_results_total"] = tot
    wins = [1.0 if h["result"] > 0 else 0.0 for h in res]
    s["win_rate"] = sum(wins) / len(wins) if wins else None
    s["win_rate_roll"] = [None if v is None else 100 * v for v in _rolling(wins, WIN_WINDOW, start=5)]
    bbs = [h["result"] / h["bb"] for h in res if h["bb"]]
    s["bb_per_100"] = 100 * sum(bbs) / len(bbs) if bbs else None

    # ---- preflop / decisions
    pre = [h for h in hands if not h["board"]]
    vp = [h for h in pre if h["taken"] in ("CALL", "RAISE", "BET")]
    s["vpip"] = len(vp) / len(pre) if pre else None
    calls = [h for h in hands if h["taken"] == "CALL" and h["call"] and h["equity"] is not None]
    s["call_margins"] = [h["equity"] - h["required"] for h in calls]
    s["call_equity"] = [h["equity"] for h in calls]
    s["call_required"] = [h["required"] for h in calls]
    s["call_labels"] = [f"{h['hole']} | {h['board'] or 'preflop'}" for h in calls]
    s["bad_calls"] = sum(1 for m in s["call_margins"] if m < -0.02)
    s["good_call_rate"] = (1 - s["bad_calls"] / len(calls)) if calls else None
    evs = [h["equity"] * (h["pot"] + h["call"]) - h["call"] for h in calls]
    s["ev_calls"] = sum(evs)
    s["ev_bad_calls"] = sum(e for e, m in zip(evs, s["call_margins"]) if m < -0.02)
    pct = lambda vals: [None if v is None else 100 * v for v in vals]
    s["call_equity_roll"] = pct(_rolling([h["equity"] for h in calls], CALL_WINDOW, start=3))
    s["call_required_roll"] = pct(_rolling([h["required"] for h in calls], CALL_WINDOW, start=3))
    judged = [h for h in hands if h["suggested"] and h["taken"]]
    s["follow_rate"] = (sum(1 for h in judged if h["suggested"] == h["taken"]) / len(judged)) if judged else None
    cnt = {}
    for h in hands:
        if h["taken"]:
            cnt[h["taken"]] = cnt.get(h["taken"], 0) + 1
    s["action_counts"] = cnt

    # ---- per session
    per = []
    for x in done:
        hs = [h for h in res if h["session_id"] == x["id"]]
        b = [h["result"] / h["bb"] for h in hs if h["bb"]]
        per.append({"label": _label(x["end_ts"]), "pl": _pl(x),
                    "hands": sum(1 for h in hands if h["session_id"] == x["id"]),
                    "bb100": 100 * sum(b) / len(b) if b else None,
                    "win_rate": (sum(1 for h in hs if h["result"] > 0) / len(hs)) if hs else None})
    s["per_session"] = per

    # ---- where you win / lose
    pos = {p: {"hands": 0, "net": 0.0} for p in POSITIONS}
    st = {n: {"hands": 0, "net": 0.0} for n in STREETS.values()}
    for h in res:
        if h["position"] in pos:
            pos[h["position"]]["hands"] += 1
            pos[h["position"]]["net"] += h["result"]
        n = len(h["board"].split()) if h["board"] else 0
        if n in STREETS:
            st[STREETS[n]]["hands"] += 1
            st[STREETS[n]]["net"] += h["result"]
    adv = {"Followed the suggestion": [], "Did something else": []}
    for h in res:
        if h["suggested"] and h["taken"]:
            adv["Followed the suggestion" if h["suggested"] == h["taken"] else "Did something else"].append(h["result"])
    s["advice_split"] = [{"name": k, "hands": len(v), "net": sum(v), "avg": sum(v) / len(v)}
                         for k, v in adv.items() if v]
    s["by_position"] = [{"name": k, **v} for k, v in pos.items() if v["hands"]]
    s["by_street"] = [{"name": k, **v} for k, v in st.items() if v["hands"]]
    return s
