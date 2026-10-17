# Commands

Start GGPoker (via Proton):

    ~/.local/bin/gg-start.sh

If it says "already running" but it isn't, clear the stale session first:

    ~/.local/bin/gg-stop.sh && ~/.local/bin/gg-start.sh

Start the study tool (opens http://127.0.0.1:5173):

    cd /home/chris/Documents/Python_Projects/Poker
    python3 server.py

Stop it: Ctrl+C in that terminal (or `pkill -f "python3 server.py"`).

Run the tests:

    python3 -m pytest -q
