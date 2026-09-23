from __future__ import annotations

import os
import socket
import sys
import threading
import webbrowser
from pathlib import Path


def executable_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def bundled_dir() -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))


def available_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def main() -> None:
    app_home = executable_dir()
    os.environ["PODCAST_APP_HOME"] = str(app_home)
    os.environ["PATH"] = f"{app_home}{os.pathsep}{os.environ.get('PATH', '')}"
    os.chdir(app_home)

    port = available_port()
    url = f"http://127.0.0.1:{port}"
    if os.getenv("PODCAST_NO_BROWSER") != "1":
        threading.Timer(1.5, webbrowser.open, args=(url,)).start()

    app_path = bundled_dir() / "app.py"
    sys.argv = [
        "streamlit",
        "run",
        str(app_path),
        "--server.address=127.0.0.1",
        f"--server.port={port}",
        "--server.headless=true",
        "--global.developmentMode=false",
        "--browser.gatherUsageStats=false",
    ]

    from streamlit.web import cli as stcli

    raise SystemExit(stcli.main())


if __name__ == "__main__":
    main()
