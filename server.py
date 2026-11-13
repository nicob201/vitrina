import sys

if sys.version_info < (3, 9):
    sys.exit("vitrina needs Python 3.9 or newer.")

from vitrina.app import main  # noqa: E402

raise SystemExit(main(sys.argv[1:]))
