"""
Demo mode for the hosted demo (see `streamlit_app.py`). Each browser session gets its own
temporary data folder, so refreshing the page starts a fresh, empty show.
"""

import os
import time
import shutil
import tempfile
from pathlib import Path

from greenbook.cli.main import get_registrar
from greenbook.data.entries import Contestant

PREFIX = "greenbook-demo-"
MAX_AGE_SECONDS = 24 * 60 * 60

# A few entrants from the README's worked example.
EXAMPLE_ENTRANTS = [
    ("Aunt Dahlia", "4,5,39,40,41,42,43,45,53,65", 0.5),
    ("Bettie Beetroot", "1,2,2,5,17,35,47,56,56,65", 0.0),
    ("Major Marrow", "21,22,30,33,39,40,41,42,43,44,45,46,47,68", 0.0),
    ("Sean Shortbread", "25A,21,22,30,44,59A", 0.0),
    ("Tommy Tomato", "4,22,33,33,44,46,47,53,56,56,59A,52", 0.0),
    ("Willy Wilja", "25A,26,26,21,44,46,47,53,59A,65", 0.0),
    ("Baby Carrot", "70,72", 0.0),
]


def enabled() -> bool:
    return os.getenv("GREENBOOK_DEMO") == "1"


def new_folder() -> Path:
    """A fresh temporary data folder. Demo folders older than a day are removed."""
    for old in Path(tempfile.gettempdir()).glob(f"{PREFIX}*"):
        if time.time() - old.stat().st_mtime > MAX_AGE_SECONDS:
            shutil.rmtree(old, ignore_errors=True)
    return Path(tempfile.mkdtemp(prefix=PREFIX))


def load_example(location: Path) -> str:
    registrar = get_registrar(location)
    for name, classes, paid in EXAMPLE_ENTRANTS:
        registrar.register(Contestant(name=name, classes=classes.split(","), paid=paid))
    return f"Loaded {len(EXAMPLE_ENTRANTS)} example entrants. Next, allocate them."
