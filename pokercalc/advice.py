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


# ---------------------------------------------------------------------------------------------
# Postflop advice v2: position, stack depth, bet sizing and draws. Rules of thumb, not a solver.
# ---------------------------------------------------------------------------------------------
# Acting later is worth equity: the "strong enough to bet/raise" line drops in position, rises out of it.
POSITION_EDGE = {"BTN": 0.03, "CO": 0.015, "HJ": 0.0, "UTG": 0.0, "SB": -0.03, "BB": -0.03}
IN_POSITION = {"BTN": "in position", "CO": "usually in position", "HJ": "in the middle", "UTG": "in the middle",
               "SB": "out of position", "BB": "out of position"}


def _chips(x):
    return int(round(x, -1)) if x >= 100 else int(round(x))


def _size(chips, pot, stack=None):
    """'~1,300 (50% of pot)' - capped at the stack."""
    if stack and chips >= stack:
        return f"all-in ({_chips(stack):,})"
    return f"~{_chips(chips):,} ({chips / pot:.0%} of pot)" if pot else f"~{_chips(chips):,}"


def suggest_postflop(eq, pot, call, opps, stack=None, position="BTN", board=(), hold=None):
    """Returns (action, why, sizing). `hold` is describe.hold_summary(); board is the list of board cards."""
    hold = hold or {}
    street = len(board)
    draws = hold.get("draws") or []
    outs = hold.get("outs") or 0
    texture = " ".join(hold.get("texture") or [])
    wet = "flush" in texture or "straight" in texture
    edge = POSITION_EDGE.get(position, 0.0)
    where = IN_POSITION.get(position, "")
    strong = strong_threshold(opps) - edge
    drawing = street < 5 and outs >= 8 and bool(draws)
    combo = street < 5 and outs >= 12
    spr = stack / pot if stack and pot else None
    req, _ = pot_odds(pot, call)

    # ---- nobody has bet: we can check or bet
    if call <= 0:
        if eq >= strong + 0.15:
            frac = 0.75 if wet else 0.5
            return "BET", (f"very strong ({eq:.0%} equity): bet big for value" +
                           (" - the board is draw-heavy, so charge them" if wet else "")), _size(pot * frac, pot, stack)
        if eq >= strong:
            frac = 0.5 if wet else 0.33
            if drawing and hold.get("made") == "High Card":
                return "BET", (f"{' + '.join(draws)} ({outs} outs): {eq:.0%} equity is already ahead of their range "
                               f"({where}), so bet - you win now or when it hits"), _size(pot * (0.66 if wet else 0.5), pot, stack)
            return "BET", (f"{eq:.0%} equity clears the {strong:.0%} value line ({where}): bet for value, "
                           f"smaller size so worse hands can call"), _size(pot * frac, pot, stack)
        if drawing and opps <= 2 and (edge >= 0 or eq >= 0.30):
            frac = 0.66 if wet else 0.5
            what = " + ".join(draws)
            return "BET", (f"semi-bluff: {what} ({outs} outs) with {eq:.0%} equity - you win if they fold "
                           f"or if you hit"), _size(pot * frac, pot, stack)
        if drawing and opps <= 2:
            return "CHECK", f"you have a draw ({outs} outs) but you're {where} - take a free card instead of bluffing", None
        return "CHECK", (f"{eq:.0%} equity is below the {strong:.0%} value line"
                         f"{' and too many opponents to bluff' if opps >= 3 and drawing else ''}"
                         f": check, keep the pot small"), None

    # ---- facing a bet
    allin = stack is not None and call >= stack
    margin = eq - req
    if margin < -0.02:
        deep = stack is not None and stack >= 6 * call
        if drawing and deep and street < 5 and margin >= -0.08:
            return "CALL", (f"short of the price ({eq:.0%} vs {req:.0%} needed) but you have {outs} outs and deep stacks: "
                            f"implied odds - you win more when it hits"), None
        return "FOLD", f"equity {eq:.0%} is below the {req:.0%} you need to call", None
    if not allin:
        raise_to = call * (3.0 if edge >= 0 else 3.5)
        commits = stack is not None and raise_to >= 0.6 * stack
        size = _size(raise_to, pot, stack) if not commits else f"all-in ({_chips(stack):,})"
        if wet and hold.get("made") == "Pair" and eq >= strong + 0.05:
            return "CALL", (f"{eq:.0%} equity beats the {req:.0%} you need, but one pair on a board where someone "
                            f"can have a straight or flush: call, don't raise - a raise is mostly called by hands that beat you"), None
        if eq >= strong + 0.05:
            return "RAISE", (f"{eq:.0%} equity is well ahead of what you need ({req:.0%}) and clears the "
                             f"{strong:.0%} line ({where}): raise for value" +
                             (" - low stack-to-pot ratio, so you're getting it in" if spr is not None and spr < 3 else "")), size
        if combo and opps == 1:
            return "RAISE", (f"semi-bluff raise: {' + '.join(draws)} ({outs} outs) - strong draw, "
                             f"fold equity plus {eq:.0%} when called"), size
    note = ""
    if spr is not None and spr > 6 and hold.get("made") in ("Pair", "High Card") and call > 0.5 * pot:
        note = " Deep stacks and a one-pair hand against a big bet: be careful about putting in more."
    if margin <= 0.02:
        return "CALL", f"marginal: equity {eq:.0%} is about break-even ({req:.0%}).{note}", None
    return "CALL", f"equity {eq:.0%} beats the {req:.0%} you need.{note}", None
