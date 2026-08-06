from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from openapi_automation.contract.sync import sync_openapi


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync OpenAPI contract from Apifox and generate diff report.")
    parser.add_argument("--source", default=None, help="Source name in config/openapi_sources.yaml.")
    parser.add_argument("--update-snapshot", action="store_true", help="Accept latest OpenAPI as the new baseline.")
    parser.add_argument("--no-fail", action="store_true", help="Do not fail when breaking changes are detected.")
    args = parser.parse_args()

    result = sync_openapi(args.source, update_snapshot=args.update_snapshot)
    diff = result["diff"]
    source = result["source"]
    summary = diff["summary"]
    print(f"OpenAPI source: {source['name']}")
    print(f"Operations: {result['latest']['operation_count']}")
    print(f"Changes: {summary['total_changes']} total, {summary['breaking_changes']} breaking")
    print(f"Diff report: {source['diff_markdown_path']}")

    should_fail = source.get("fail_on_breaking_change", True) and diff["has_breaking_changes"] and not args.no_fail
    return 2 if should_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
