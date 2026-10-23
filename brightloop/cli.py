"""Command line: run --input cases.json --output result.json"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from .core import run
from .sources import file as file_source


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="brightloop", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    run_cmd = sub.add_parser("run", help="Process a cases.json file into result.json")
    run_cmd.add_argument("--input", required=True, help="Path to cases.json")
    run_cmd.add_argument("--output", required=True, help="Where to write result.json")
    args = parser.parse_args(argv)

    payload, load_errors = file_source.load(args.input)
    result = run(payload, started_at=datetime.now(timezone.utc))
    result["run"]["errors"][:0] = load_errors
    result["run"]["mode"] = "file"

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    items, skipped, errors = len(result["items"]), len(result["skipped"]), len(result["run"]["errors"])
    print(f"Wrote {out}: {items} item(s), {skipped} skipped, {errors} error(s).", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
