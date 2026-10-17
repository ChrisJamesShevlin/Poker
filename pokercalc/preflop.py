"""Simple 6-max preflop guide built from hand charts. A rough guide, NOT a solver.

Charts are approximate, commonly published ~100bb 6-max ranges. Medium stacks
(15-40bb) use the same chart trimmed to its stronger hands; short stacks (<15bb)
use a push/fold list.
"""
import math
import re

from .parser import RANKS
from .ranges import combos, hole_class, ranking

POSITIONS = ["UTG", "HJ", "CO", "BTN", "SB", "BB"]
_R = {r: i for i, r in enumerate(RANKS)}


def expand(spec):
    """'22+, A2s+, KTs+, JTs, AJo+, 66-TT' -> set of hand classes like {'AA','AKs','AJo'}."""
    out = set()
    for tok in (t.strip() for t in spec.split(",") if t.strip()):
        m = re.fullmatch(r"([2-9TJQKA])([2-9TJQKA])([so]?)(\+|-([2-9TJQKA])([2-9TJQKA])[so]?)?", tok)
        if not m:
            raise ValueError(f"bad chart token {tok!r}")
        a, b, kind, suffix, c, _d = m.groups()
        if a == b:  # pairs
            lo, hi = _R[a], _R[a]
            if suffix == "+":
                hi = len(RANKS) - 1
            elif suffix:
                hi = max(_R[a], _R[c])
                lo = min(_R[a], _R[c])
            for i in range(lo, hi + 1):
                out.add(RANKS[i] * 2)
        else:
            hi_r, lo_r = (a, b) if _R[a] > _R[b] else (b, a)
            lows = [lo_r]
            if suffix == "+":
                lows = [RANKS[i] for i in range(_R[lo_r], _R[hi_r])]
            for l in lows:
                out.add(hi_r + l + kind)
    return out


def _n(cs):
    return sum(len(combos(c)) for c in cs)


# Raise-first-in (open) charts, ~100bb
OPEN = {
    "UTG": expand("22+, A2s+, KTs+, QTs+, JTs, T9s, 98s, 87s, 76s, AJo+, KQo"),
    "HJ": expand("22+, A2s+, K9s+, Q9s+, J9s+, T9s, 98s, 87s, 76s, 65s, ATo+, KJo+, QJo"),
    "CO": expand("22+, A2s+, K6s+, Q8s+, J8s+, T8s+, 97s+, 86s+, 75s+, 65s, 54s, A9o+, KTo+, QTo+, JTo"),
    "BTN": expand("22+, A2s+, K2s+, Q4s+, J6s+, T6s+, 96s+, 85s+, 75s+, 64s+, 54s, "
                  "A2o+, K8o+, Q9o+, J8o+, T8o+, 98o, 87o"),
    "SB": expand("22+, A2s+, K2s+, Q5s+, J7s+, T7s+, 97s+, 86s+, 76s, 65s, 54s, A2o+, K9o+, Q9o+, J9o+, T9o"),
}
# Facing a single raise: re-raise (3-bet) and call charts by your position
THREE_BET = expand("JJ+, AQs+, AKo, A5s, A4s")
CALL = {
    "UTG": expand("66-TT, ATs+, KQs, KJs, QJs, JTs, T9s, AQo"),
    "HJ": expand("66-TT, ATs+, KJs+, QJs, JTs, T9s, 98s, AQo"),
    "CO": expand("55-TT, A9s+, KTs+, QTs+, JTs, T9s, 98s, 87s, AQo, KQo"),
    "BTN": expand("22-TT, A2s+, K9s+, Q9s+, J9s+, T9s, 98s, 87s, 76s, 65s, AJo+, KQo"),
    "SB": expand("77-TT, ATs+, KQs, QJs, JTs, AQo"),
    "BB": expand("22-TT, A2s+, K5s+, Q7s+, J8s+, T8s+, 97s+, 86s+, 75s+, 65s, 54s, ATo+, KTo+, QTo+, JTo"),
}
# Short stack (<15bb) push list as a % of hands (by strength); BB = calling a shove
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


def tier(pct):
    return ("Premium" if pct <= 3 else "Strong" if pct <= 10 else "Playable" if pct <= 25
            else "Speculative" if pct <= 45 else "Weak")


def describe_class(cls):
    if len(cls) == 2:
        return f"pocket pair ({cls[0]}s)"
    hi, lo, kind = cls
    gap = _R[hi] - _R[lo]
    suited = kind == "s"
    if hi == "A" and suited:
        return "suited ace"
    if hi in "AKQJT" and lo in "AKQJT":
        return "suited broadway" if suited else "offsuit broadway"
    if gap == 1:
        return "suited connector" if suited else "offsuit connector"
    if gap == 2 and suited:
        return "suited one-gapper"
    return "suited hand" if suited else "offsuit hand"


def _trim(chart, bb):
    """15-25bb: keep only the stronger ~85% of the chart's hands."""
    if bb is None or bb >= 25:
        return chart
    order = [c for c in ranking() if c in chart]
    return set(order[: math.ceil(len(order) * 0.85)])


def advise(hole, position, stack_bb, facing_raise):
    cls = hole_class(*hole)
    rank = ranking().index(cls) + 1
    pct = percentile(cls)
    band = stack_band(stack_bb)
    head = (f"{cls} - {tier(pct)} {describe_class(cls)}: rank {rank}/169 (top {pct:.0f}% of hands). "
            f"Stack: {band}" + (f" ({stack_bb:.0f}bb)" if stack_bb else "") + f". Position {position}.")
    if band == "short":
        lim = SHOVE[position]
        if pct <= lim:
            act, why = "RAISE", f"short stack: shove/call-shove range ~top {lim}% from {position} - this hand is in it"
        else:
            act, why = "FOLD", f"outside the ~top {lim}% short-stack range for {position}"
    elif not facing_raise:
        if position == "BB":
            act, why = "CHECK", "nobody raised; you see a free flop"
        else:
            chart = _trim(OPEN[position], stack_bb)
            share = 100 * _n(chart) / 1326
            if cls in chart:
                act, why = "RAISE", f"in the {position} open chart (~{share:.0f}% of hands)"
            else:
                act, why = "FOLD", f"not in the {position} open chart (~{share:.0f}% of hands)"
    else:
        call = _trim(CALL[position], stack_bb)
        if cls in THREE_BET:
            act, why = "RAISE", "premium or good bluff-3-bet hand: re-raise"
        elif cls in call:
            act, why = "CALL", f"in the {position} calling chart vs a raise"
        else:
            act, why = "FOLD", f"not in the {position} calling chart vs a raise"
    return {"action": act, "text": head, "why": why, "class": cls, "rank": rank, "pct": pct}
