"""
Start the Greenbook web UI and open it in the default browser.
"""

import os
import sys
import socket
import argparse
import threading
import webbrowser
from pathlib import Path


def _open_browser_when_ready(port: int):
    for _ in range(300):  # up to a minute
        try:
            with socket.create_connection(("localhost", port), timeout=0.2):
                webbrowser.open(f"http://localhost:{port}")
                return
        except OSError:
            threading.Event().wait(0.2)


def main():
    parser = argparse.ArgumentParser(description="Start the Greenbook web UI.")
    parser.add_argument(
        "--location",
        help="Folder holding the show data (default: $GREENBOOK_LOCATION or ~/greenbook-data).",
    )
    parser.add_argument("--port", type=int, default=8501)
    args = parser.parse_args()
    if args.location:
        os.environ["GREENBOOK_LOCATION"] = str(Path(args.location).expanduser().resolve())

    from streamlit.web import cli as stcli

    threading.Thread(target=_open_browser_when_ready, args=(args.port,), daemon=True).start()
    sys.argv = [
        "streamlit",
        "run",
        str(Path(__file__).with_name("app.py")),
        "--server.address=localhost",  # only reachable from this computer
        f"--server.port={args.port}",
        "--server.headless=true",  # we open the browser ourselves; avoids a first-run prompt
        "--server.fileWatcherType=none",
        "--browser.gatherUsageStats=false",
        "--client.toolbarMode=minimal",
    ]
    sys.exit(stcli.main())
