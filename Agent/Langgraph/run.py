from __future__ import annotations

import threading
import webbrowser
from time import sleep

from backend.server import create_server


def main() -> None:
    server = create_server()
    url = f"http://{server.server_address[0]}:{server.server_address[1]}"

    print("=" * 60)
    print("OtariFlow — Intelligent AI Routing Platform")
    print(f"Backend + Frontend: {url}")
    print("API Health:        /api/health")
    print("API Prompt:        /api/prompt")
    print("=" * 60)

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    sleep(0.7)
    try:
        webbrowser.open(url)
    except Exception:
        pass

    try:
        thread.join()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()


if __name__ == "__main__":
    main()
