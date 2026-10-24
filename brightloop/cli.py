"""Command line: run --input cases.json --output result.json"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .env import load_dotenv
from .file_run import run_file
from .live_run import ROOT, live
from .store.base44 import Base44Store
from .store.publish import publish_run


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="brightloop", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    run_cmd = sub.add_parser("run", help="Process a cases.json file into result.json")
    run_cmd.add_argument("--input", required=True, help="Path to cases.json")
    run_cmd.add_argument("--output", required=True, help="Where to write result.json")
    live_cmd = sub.add_parser("live", help="Capture pricing pages, diff against the last recording, decide")
    live_cmd.add_argument("--config", default=str(ROOT / "config/live.json"))
    live_cmd.add_argument("--recordings", default=str(ROOT / "recordings"))
    live_cmd.add_argument("--output", help="Also write result.json here")
    live_cmd.add_argument("--offline", action="store_true", help="No network: replay the two latest recordings")
    live_cmd.add_argument("--no-publish", action="store_true", help="Don't write to Base44 even if keys are set")
    pub_cmd = sub.add_parser("publish", help="Upload a recorded run to Base44 (needs BASE44_APP_ID, BASE44_TOKEN)")
    pub_cmd.add_argument("--run", help="Run folder name under recordings/runs (default: the latest)")
    pub_cmd.add_argument("--config", default=str(ROOT / "config/live.json"))
    pub_cmd.add_argument("--recordings", default=str(ROOT / "recordings"))
    args = parser.parse_args(argv)
    load_dotenv(ROOT / ".env")

    if args.command == "publish":
        store = Base44Store.from_env()
        if store is None:
            print("Set BASE44_APP_ID and BASE44_TOKEN (in .env or the environment) to publish.", file=sys.stderr)
            return 2
        recordings = Path(args.recordings)
        runs = sorted(p for p in (recordings / "runs").iterdir() if p.is_dir()) if (recordings / "runs").exists() else []
        run_dir = recordings / "runs" / args.run if args.run else (runs[-1] if runs else None)
        if run_dir is None or not run_dir.exists():
            print("No recorded run to publish.", file=sys.stderr)
            return 2
        names = [c["name"] for c in json.loads(Path(args.config).read_text())["competitors"] if c.get("enabled")]
        errors = publish_run(store, run_dir, recordings, ROOT, names)
        print(f"Published {run_dir.name}: {len(errors)} error(s).", file=sys.stderr)
        for e in errors:
            print(f"  {e}", file=sys.stderr)
        return 1 if errors else 0

    if args.command == "live":
        store = None if (args.offline or args.no_publish) else Base44Store.from_env()
        result = live(Path(args.config), Path(args.recordings), Path(args.output) if args.output else None,
                      args.offline, store)
        print(f"{result['run']['mode']}: {len(result['items'])} item(s), {len(result['skipped'])} skipped, "
              f"{len(result['run']['errors'])} error(s).", file=sys.stderr)
        return 0

    result = run_file(args.input)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    items, skipped, errors = len(result["items"]), len(result["skipped"]), len(result["run"]["errors"])
    print(f"Wrote {out}: {items} item(s), {skipped} skipped, {errors} error(s).", file=sys.stderr)
    return 0


def run_command() -> int:
    """Entry point for the installed `run` command: `run --input cases.json --output result.json`."""
    return main(["run", *sys.argv[1:]])


if __name__ == "__main__":
    sys.exit(main())
