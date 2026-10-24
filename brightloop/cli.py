"""Command line: run --input cases.json --output result.json"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from .env import load_dotenv
from .file_run import run_file
from .live_run import ROOT, live
from .notify import deck_message, post
from .store.base44 import Base44Error, Base44Store
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
    mark_cmd = sub.add_parser("mark", help="Set a run's status in Base44 (used by the weekly workflow)")
    mark_cmd.add_argument("--run-key", required=True)
    mark_cmd.add_argument("--status", required=True, choices=["running", "failed"])
    mark_cmd.add_argument("--error", help="Why it failed")
    mark_cmd.add_argument("--log-url", help="Link to the workflow log")
    notify_cmd = sub.add_parser("notify", help="Post the Monday Slack message (needs SLACK_WEBHOOK_URL)")
    notify_cmd.add_argument("--deck", required=True, help="build-deck's JSON response")
    args = parser.parse_args(argv)
    load_dotenv(ROOT / ".env")

    if args.command == "notify":
        webhook = os.environ.get("SLACK_WEBHOOK_URL", "").strip()
        try:
            deck = json.loads(Path(args.deck).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            deck = None
        text = deck_message(deck if isinstance(deck, dict) else None)
        if not webhook:
            print(f"No SLACK_WEBHOOK_URL; would have sent:\n{text}", file=sys.stderr)
            return 0
        try:
            post(webhook, text)
        except OSError as exc:  # URLError and HTTPError are OSErrors; never fail the run over a ping
            print(f"Couldn't post to Slack: {exc}", file=sys.stderr)
        return 0

    if args.command == "mark":
        store = Base44Store.from_env()
        if store is None:
            print("No Base44 keys; nothing to mark.", file=sys.stderr)
            return 0
        record = {"run_key": args.run_key, "status": args.status, "mode": "live"}
        if args.status == "running":
            record["started_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        if args.error:
            record["errors"] = [args.error]
        if args.log_url:
            record["log_url"] = args.log_url
        try:
            store.upsert("Run", "run_key", [record])
        except Base44Error as exc:  # never fail the workflow over a status write
            print(f"Couldn't mark the run: {exc}", file=sys.stderr)
        return 0

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
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    except OSError as exc:
        print(f"Couldn't write {out}: {exc.strerror or exc}", file=sys.stderr)
        return 2

    items, skipped, errors = len(result["items"]), len(result["skipped"]), len(result["run"]["errors"])
    print(f"Wrote {out}: {items} item(s), {skipped} skipped, {errors} error(s).", file=sys.stderr)
    return 0


def run_command() -> int:
    """Entry point for the installed `run` command: `run --input cases.json --output result.json`."""
    return main(["run", *sys.argv[1:]])


if __name__ == "__main__":
    sys.exit(main())
