"""Glue: one evaluate() call used by the web UI."""
from . import advice, describe, preflop
from .equity import equity
from .oprange import resolve
from .parser import Query
from .potodds import pot_odds, verdict


def evaluate(d, sims=20000):
    hole, board = d["hole"], d["board"]
    pot, call = float(d.get("pot") or 0), float(d.get("call") or 0)
    opps = int(d.get("opps") or 1)
    stack = float(d["stack"]) if d.get("stack") else None
    bb = float(d["bb"]) if d.get("bb") else None
    position = d.get("position") or "BTN"

    # Preflop: the raise size is worked out from 'bet to call' alone
    rinfo = None if board else preflop.raise_info(call, bb, stack, position)
    facing = bool(d.get("facing"))
    if rinfo and (bb or rinfo["tier"] == "shove"):
        facing = rinfo["facing"]          # detected, so the toggle isn't needed
    tier = rinfo["tier"] if rinfo and facing else "normal"
    steps = {"big": 1, "shove": 2}.get(tier, 0)

    mode = d.get("range_mode", d.get("range_pct") or 0)
    classes, rlabel, rpct, pct = None, "Random hands", None, None
    if mode == "auto":
        classes, rlabel, rpct = resolve(pot, call, len(board), d.get("raiser") or None,
                                        d.get("table") or "normal", bool(d.get("multi_street")),
                                        extra_steps=steps)
        rlabel = "Auto: " + rlabel
    elif mode:
        pct = int(mode)
        rlabel, rpct = f"Top {pct}% (you chose)", pct
    win, tie, eq = equity(hole, board, opps, pct, sims=sims, range_classes=classes)
    req, ratio = pot_odds(pot, call)
    out = {"equity": eq, "win": win, "tie": tie, "required": req, "ratio": ratio,
           "verdict": verdict(eq, pot, call) if call > 0 else None,
           "hold": None, "outs": None, "rule24": None, "preflop": None,
           "stack_line": None, "random_warning": mode == 0 or mode is None,
           "range_label": rlabel, "range_pct_used": rpct}
    if stack:
        out["stack_line"] = (f"Stack {stack:,.0f}" + (f" ({stack/bb:.0f}bb)" if bb else "") +
                             (f" - SPR {stack/pot:.1f}" if pot else "") +
                             (" - call puts you all-in" if call and call >= stack else ""))
    action, why = advice.suggest(eq, pot, call, opps, stack)
    sizing = None
    if board:
        info = describe.analyse(hole, board)
        out["hold"] = describe.hold_summary(hole, board)
        if info["outs"]:
            out["outs"] = info["outs"]
            r = describe.rule_of_2_and_4(info["outs"], len(board))
            out["rule24"] = r[1] if r else None
        action, why, sizing = advice.suggest_postflop(eq, pot, call, opps, stack, position, board, out["hold"])
    else:
        g = preflop.advise(hole, position, stack / bb if stack and bb else None, facing, tier,
                           rinfo["raise_bb"] if rinfo else None)
        out["preflop"] = {"text": g["text"], "why": g["why"]}
        if rinfo and rinfo["tier"] != "none":
            names = {"limp": "limped pot (no raise)", "normal": "normal-size raise",
                     "big": "big raise (likely a 3-bet)", "shove": "huge raise or shove"}
            out["preflop"]["size"] = (f"~{rinfo['raise_bb']:.1f}bb - " if rinfo["raise_bb"] else "") + names[rinfo["tier"]]
        out["hold"] = {"title": f"{g['class']} - {preflop.describe_class(g['class'])}",
                       "tier": f"{preflop.tier(g['pct'])} hand, rank {g['rank']}/169 (top {g['pct']:.0f}%)",
                       "draws": [], "texture": [], "nuts": None, "ahead": None, "outs": None}
        action, why = g["action"], g["why"]
        if call > 0 and action == "CALL" and eq < req - 0.02:
            out["preflop"]["note"] = f"Guide says call, but pot odds need {req:.0%} and you have {eq:.0%}."
    out["action"], out["why"], out["sizing"] = action, why, sizing
    return out
