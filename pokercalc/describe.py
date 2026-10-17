"""Plain-English hand description, outs, and the rule of 2 and 4."""
from collections import Counter

import eval7

from .equity import FULL_DECK
from .parser import RANKS

CATS = ["High Card", "Pair", "Two Pair", "Trips", "Straight", "Flush",
        "Full House", "Quads", "Straight Flush"]
NAMES = {"2": "deuce", "3": "three", "4": "four", "5": "five", "6": "six", "7": "seven",
         "8": "eight", "9": "nine", "T": "ten", "J": "jack", "Q": "queen", "K": "king", "A": "ace"}


def _cat(cards):
    return CATS.index(eval7.handtype(eval7.evaluate([eval7.Card(c) for c in cards])))


def _pair_text(hole, board):
    rb = sorted((RANKS.index(c[0]) for c in board), reverse=True)
    hr = [RANKS.index(c[0]) for c in hole]
    if hr[0] == hr[1]:
        if hr[0] > rb[0]:
            return "overpair"
        return "pocket pair below the top board card"
    mine = [r for r in hr if r in rb]
    if not mine:
        return "pair on the board only (you have no pair of your own)"
    r = mine[0]
    uniq = sorted(set(rb), reverse=True)
    pos = uniq.index(r)
    label = "top pair" if pos == 0 else "bottom pair" if r == uniq[-1] else "middle pair"
    kicker = NAMES[RANKS[max(h for h in hr if h != r)]]
    return f"{label} ({NAMES[RANKS[r]]}s, {kicker} kicker)"


def _straight_draw_ranks(hole, board):
    """Ranks that would complete a straight using at least one hole card."""
    have = {RANKS.index(c[0]) + 2 for c in hole + board}
    hole_r = {RANKS.index(c[0]) + 2 for c in hole}
    if 14 in have:
        have.add(1)
        if 14 in hole_r:
            hole_r.add(1)
    out = set()
    for r in range(2, 15):
        if r in have:
            continue
        s = have | {r} | ({1} if r == 14 else set())
        for low in range(1, 11):
            win = set(range(low, low + 5))
            if win <= s and r in win and win & hole_r:
                out.add(r)
    return out


def analyse(hole, board):
    """Returns dict: text, outs (int), outs_note, draws list."""
    if len(board) < 3:
        return {"text": "Preflop", "outs": 0, "draws": [], "made": None}
    cards = hole + board
    made = CATS[_cat(cards)]
    parts = []
    if made == "Pair":
        parts.append(_pair_text(hole, board))
    elif made == "High Card":
        parts.append("high card (no pair)")
    else:
        note = " (board plays)" if len(board) == 5 and _cat(board) == _cat(cards) else ""
        parts.append(made.lower() + note)
    draws = []
    if len(board) < 5 and made not in ("Straight", "Flush", "Full House", "Quads", "Straight Flush"):
        suits = Counter(c[1] for c in cards)
        for s, n in suits.items():
            mine = sum(1 for c in hole if c[1] == s)
            if n == 4 and mine:
                draws.append("flush draw")
            elif n == 3 and mine and len(board) == 3:
                draws.append("backdoor flush draw")
        sr = _straight_draw_ranks(hole, board)
        if len(sr) >= 2:
            draws.append("open-ended straight draw")
        elif len(sr) == 1:
            draws.append("gutshot straight draw")
    parts += draws
    text = ", ".join(parts)

    outs = 0
    if len(board) < 5:
        base = _cat(cards)
        dead = set(cards)
        for c in FULL_DECK:
            if c in dead:
                continue
            new = _cat(cards + [c])
            if new <= base or new < 2:
                continue  # only count real improvements (two pair or better)
            if new == 2 and c[0] not in (hole[0][0], hole[1][0]):
                continue  # two pair made only via the board's cards is weak
            if len(board) >= 4 and _cat(board + [c]) >= new:
                continue  # the board alone would give everyone this hand
            outs += 1
    return {"text": text, "outs": outs, "draws": draws, "made": made}


def rule_of_2_and_4(outs, board_len):
    """Returns (approx_equity_fraction, explanation) or None on river/preflop."""
    if board_len == 3:
        return min(outs * 4, 100) / 100, f"{outs} outs x 4 = ~{min(outs*4,100)}% (flop, two cards to come)"
    if board_len == 4:
        return min(outs * 2, 100) / 100, f"{outs} outs x 2 = ~{min(outs*2,100)}% (turn, one card to come)"
    return None
