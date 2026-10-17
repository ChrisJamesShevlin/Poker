# Poker Study Tool (play-money only)

Manual-entry equity / pot-odds / analytics app. No screen reading, OCR, overlay or client automation.

    python3 server.py       # opens the app in your browser (localhost only)
    python3 -m pytest -q    # tests

Needs: eval7, flask (Chart.js is bundled in static/. Data is stored in `poker.db` (local SQLite).

Limits: it knows nothing about how your opponents play, it is not a GTO solver, and the
preflop guide and check/call/raise suggestion are simple rules of thumb.
