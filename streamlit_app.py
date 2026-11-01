"""
Entry point for the hosted demo on Streamlit Community Cloud. It runs the normal web UI in
demo mode: every visitor gets a temporary, empty show that a page refresh throws away.

To run Greenbook on your own computer, use `greenbook-ui` instead.
"""

import os
import runpy
from pathlib import Path

import greenbook.ui

os.environ["GREENBOOK_DEMO"] = "1"
runpy.run_path(str(Path(greenbook.ui.__file__).with_name("app.py")), run_name="__main__")
