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
    mode = d.get("range_mode", d.get("range_pct") or 0)
    classes, rlabel, rpct = None, "Random hands", None
    if mode == "auto":
        classes, rlabel, rpct = resolve(pot, call, len(board), d.get("raiser") or None,
                                        d.get("table") or "normal", bool(d.get("multi_street")))
        rlabel = "Auto: " + rlabel
    elif mode:
        pct = int(mode)
        rlabel, rpct = f"Top {pct}% (you chose)", pct
    else:
        pct = None
    pct = int(mode) if mode and mode != "auto" else None
    stack, bb = d.get("stack") or None, d.get("bb") or None
    stack = float(stack) if stack else None
    bb = float(bb) if bb else None
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
    if board:
        info = describe.analyse(hole, board)
        out["hold"] = describe.hold_summary(hole, board)
        if info["outs"]:
            out["outs"] = info["outs"]
            r = describe.rule_of_2_and_4(info["outs"], len(board))
            out["rule24"] = r[1] if r else None
    else:
        g = preflop.advise(hole, d.get("position") or "BTN", stack / bb if stack and bb else None,
                           bool(d.get("facing")))
        out["preflop"] = {"text": g["text"], "why": g["why"]}
        out["hold"] = {"title": f"{g['class']} - {preflop.describe_class(g['class'])}",
                       "tier": f"{preflop.tier(g['pct'])} hand, rank {g['rank']}/169 (top {g['pct']:.0f}%)",
                       "draws": [], "texture": [], "nuts": None, "ahead": None, "outs": None}
        action, why = g["action"], g["why"]
        if call > 0 and action == "CALL" and eq < req - 0.02:
            out["preflop"]["note"] = f"Guide says call, but pot odds need {req:.0%} and you have {eq:.0%}."
    out["action"], out["why"] = action, why
    return out
