"""Stats over logged sessions/hands."""


def summary(con):
    s = {}
    sess = con.execute("SELECT * FROM sessions ORDER BY id").fetchall()
    hands = con.execute("SELECT h.*, s.bb AS bb FROM hands h LEFT JOIN sessions s ON s.id=h.session_id "
                        "ORDER BY h.ts").fetchall()
    done = [x for x in sess if x["balance_after"] is not None]
    s["sessions"] = len(sess)
    s["hands"] = len(hands)
    s["balance_points"] = []
    if done:
        s["balance_points"].append(done[0]["balance_before"])
        s["balance_points"] += [x["balance_after"] for x in done]
    s["session_pl"] = [x["balance_after"] - x["balance_before"] for x in done]
    s["total_pl"] = sum(s["session_pl"])
    res = [h for h in hands if h["result"] is not None]
    cum, tot = [], 0.0
    for h in res:
        tot += h["result"]
        cum.append(tot)
    s["cum_results"] = cum
    s["hand_results_total"] = tot
    bbs = [h["result"] / h["bb"] for h in res if h["bb"]]
    s["bb_per_100"] = 100 * sum(bbs) / len(bbs) if bbs else None
    pre = [h for h in hands if not h["board"]]
    vp = [h for h in pre if h["taken"] in ("CALL", "RAISE", "BET")]
    s["vpip"] = len(vp) / len(pre) if pre else None
    calls = [h for h in hands if h["taken"] == "CALL" and h["call"] and h["equity"] is not None]
    s["call_margins"] = [h["equity"] - h["required"] for h in calls]
    s["bad_calls"] = sum(1 for m in s["call_margins"] if m < -0.02)
    judged = [h for h in hands if h["suggested"] and h["taken"]]
    s["follow_rate"] = (sum(1 for h in judged if h["suggested"] == h["taken"]) / len(judged)) if judged else None
    cnt = {}
    for h in hands:
        if h["taken"]:
            cnt[h["taken"]] = cnt.get(h["taken"], 0) + 1
    s["action_counts"] = cnt
    return s
