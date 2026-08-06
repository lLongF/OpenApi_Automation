from __future__ import annotations

import argparse
import sys
from pathlib import Path

import uvicorn


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    parser = argparse.ArgumentParser(description="Start the OpenAPI Automation web console.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8000, type=int)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    uvicorn.run("web.backend.app:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
