from __future__ import annotations

from .server import create_server


def main() -> None:
    server = create_server()
    try:
        server.serve_forever()
    finally:
        server.server_close()
