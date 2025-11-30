"""Flask entrypoint.

Supports running both as a module (python -m views.app) and as a script
(python views/app.py) by importing create_app from the views package.
"""
import os
import sys


# Ensure project root is on sys.path when executed as a script
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from views import create_app  # type: ignore


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
