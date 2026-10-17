"""Turns equity + pot odds into a simple check/call/raise/fold suggestion."""
from .potodds import pot_odds

# Equity (vs the opponent model you picked) above which we lean toward betting/raising for value.
STRONG = {1: 0.65, 2: 0.50, 3: 0.42}


def strong_threshold(opps):
    return STRONG.get(opps, 0.36)


def suggest(eq, pot, call, opps, stack=None):
    req, _ = pot_odds(pot, call)
    strong = strong_threshold(opps)
    if call <= 0:
        if eq >= strong:
            return "BET", f"equity {eq:.0%} >= {strong:.0%}: bet for value (~2/3 pot = {pot*2/3:,.0f})"
        return "CHECK", f"equity {eq:.0%} is below the {strong:.0%} value-bet line"
    allin = stack is not None and call >= stack
    margin = eq - req
    if margin < -0.02:
        return "FOLD", f"equity {eq:.0%} < break-even {req:.0%}"
    if eq >= strong and not allin:
        return "RAISE", f"equity {eq:.0%} is strong ({strong:.0%}+ line) and beats break-even {req:.0%}"
    if margin <= 0.02:
        return "CALL", f"marginal: equity {eq:.0%} ~ break-even {req:.0%}"
    return "CALL", f"equity {eq:.0%} > break-even {req:.0%}"
