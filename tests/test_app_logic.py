import time
from pokercalc import advice, analytics, describe, preflop, store
from pokercalc.parser import Query


def test_describe_bottom_pair():
    r = describe.analyse(["6d", "5h"], ["5s", "7h", "Qh"])
    assert "bottom pair" in r["text"] and "backdoor flush" in r["text"]

def test_outs_flush_plus_gutshot():
    assert describe.analyse(["Ah", "Kh"], ["Qh", "Jh", "2c"])["outs"] == 12

def test_outs_open_ended():
    assert describe.analyse(["9h", "8h"], ["7c", "6d", "2s"])["outs"] == 8

def test_rule_of_4():
    assert describe.rule_of_2_and_4(8, 3)[0] == 0.32

def test_preflop():
    assert preflop.advise(["Ah", "Kd"], "UTG", 100, False)["action"] == "RAISE"
    assert preflop.advise(["7h", "2d"], "BTN", 100, False)["action"] == "FOLD"
    assert preflop.advise(["7h", "2d"], "BB", 100, False)["action"] == "CHECK"
    assert preflop.advise(["Ah", "Ad"], "CO", 100, True)["action"] == "RAISE"

def test_advice():
    assert advice.suggest(0.20, 1000, 500, 1)[0] == "FOLD"
    assert advice.suggest(0.80, 1000, 300, 1)[0] == "RAISE"
    assert advice.suggest(0.80, 1000, 0, 1)[0] == "BET"
    assert advice.suggest(0.30, 1000, 0, 1)[0] == "CHECK"

def test_store_and_analytics(tmp_path):
    con = store.connect(tmp_path / "t.db")
    sid = store.start_session(con, 10000, 2000, 20)
    q = Query(["Ah", "Kd"], [], 60, 40, 1, None)
    store.log_hand(con, sid, q, "BTN", 2000, 0.6, 0.4, "CALL", "CALL", 100)
    store.log_hand(con, sid, q, "BTN", 2000, 0.3, 0.4, "FOLD", "CALL", -40)
    store.end_session(con, sid, 10500)
    s = analytics.summary(con)
    assert s["hands"] == 2 and s["total_pl"] == 500
    assert s["cum_results"] == [100, 60] and s["bad_calls"] == 1
    assert s["follow_rate"] == 0.5 and s["vpip"] == 1.0


def test_hand_names():
    n = describe.made_hand_name
    assert n(["Ah", "Kh", "Qh", "Jh", "2h"]) == "Flush, Ace high"
    assert n(["9h", "8h", "7c", "6d", "5s"]) == "Straight, Nine high"
    assert n(["Ah", "2d", "3c", "4s", "5h"]) == "Straight, Five high"
    assert n(["Ah", "Ad", "Kc", "Ks", "2d"]) == "Two pair, Aces and Kings"
    assert n(["5h", "5d", "5s", "Kc", "Kd"]) == "Full house, Fives full of Kings"

def test_hold_summary():
    r = describe.hold_summary(["Ah", "Kh"], ["Qh", "Jh", "2h"])
    assert r["title"].startswith("Flush, Ace high") and "best possible" in r["nuts"]
    r = describe.hold_summary(["6d", "5h"], ["5s", "7h", "Qh"])
    assert "bottom pair" in r["title"] and "backdoor flush draw" in r["draws"]

def test_chart_sizes():
    from pokercalc.preflop import OPEN, _n
    pct = {k: 100 * _n(v) / 1326 for k, v in OPEN.items()}
    assert 14 < pct["UTG"] < 18 and 40 < pct["BTN"] < 50

def test_preflop_charts():
    assert preflop.advise(["7h", "6h"], "BTN", 100, False)["action"] == "RAISE"
    assert preflop.advise(["7h", "6h"], "UTG", 100, False)["action"] == "RAISE"
    assert preflop.advise(["7h", "2d"], "UTG", 100, False)["action"] == "FOLD"
    assert preflop.advise(["9h", "9d"], "BTN", 100, True)["action"] == "CALL"
