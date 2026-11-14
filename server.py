#!/usr/bin/env python3
import signal
import sys

if sys.version_info < (3, 9):
    sys.exit("vitrina needs Python 3.9 or newer.")

from vitrina.app import main  # noqa: E402

# `python3 server.py stop` sends SIGTERM: stop the way Ctrl+C does, letting go of everything.
signal.signal(signal.SIGTERM, signal.default_int_handler)
raise SystemExit(main(sys.argv[1:]))
