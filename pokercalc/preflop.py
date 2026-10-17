"""Simple 6-max preflop guide. A rough guide, NOT a solver."""
from .ranges import combos, hole_class, ranking

POSITIONS = ["UTG", "HJ", "CO", "BTN", "SB", "BB"]
# Percent of hands (by combos) -- rough, commonly quoted 6-max figures.
OPEN = {"UTG": 14, "HJ": 18, "CO": 25, "BTN": 42, "SB": 40}
CALL_RAISE = {"UTG": 8, "HJ": 10, "CO": 12, "BTN": 15, "SB": 6, "BB": 28}
THREE_BET = 4
SHOVE = {"UTG": 10, "HJ": 13, "CO": 18, "BTN": 30, "SB": 40, "BB": 22}


def stack_band(bb):
    if bb is None:
        return "unknown"
    return "short" if bb < 15 else "medium" if bb < 40 else "deep"


def percentile(cls):
    """Cumulative % of all hands that are as strong or stronger."""
    got = 0
    for c in ranking():
        got += len(combos(c))
        if c == cls:
            return 100 * got / 1326


def advise(hole, position, stack_bb, facing_raise):
    cls = hole_class(*hole)
    rank = ranking().index(cls) + 1
    pct = percentile(cls)
    band = stack_band(stack_bb)
    head = f"{cls}: strength rank {rank}/169 (top {pct:.0f}% of hands). Stack: {band}" + \
           (f" ({stack_bb:.0f}bb)" if stack_bb else "") + f". Position {position}."
    scale = 0.85 if band == "medium" else 1.0
    if band == "short":
        lim = SHOVE[position]
        if pct <= lim:
            act, why = "RAISE", f"short stack: shove/call-shove range ~top {lim}% from {position}"
        else:
            act, why = "FOLD", f"outside the ~top {lim}% short-stack range for {position}"
    elif not facing_raise:
        if position == "BB":
            act, why = "CHECK", "nobody raised; you see a free flop"
        else:
            lim = OPEN[position] * scale
            act, why = ("RAISE", f"open-raise range ~top {lim:.0f}%") if pct <= lim else \
                       ("FOLD", f"outside the ~top {lim:.0f}% open range for {position}")
    else:
        if pct <= THREE_BET * scale:
            act, why = "RAISE", f"premium: 3-bet (top {THREE_BET}%)"
        elif pct <= CALL_RAISE[position] * scale:
            act, why = "CALL", f"within ~top {CALL_RAISE[position]*scale:.0f}% calling range vs a raise from {position}"
        else:
            act, why = "FOLD", "too weak to continue vs a raise"
    return {"action": act, "text": head, "why": why, "class": cls, "rank": rank, "pct": pct}
