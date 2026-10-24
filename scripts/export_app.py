"""Copy the Base44 app's source code into app/ (the web front end and its backend function).

  python3 scripts/export_app.py

Needs BASE44_APP_ID and BASE44_TOKEN (in .env). The app is edited in Base44; this keeps a
copy in the repo so all the code lives here. Re-run it after changing the app and commit the
result. Build output and dependencies are left out.
"""

import io
import json
import os
import shutil
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib import request

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from brightloop.env import load_dotenv  # noqa: E402
from brightloop.store.base44 import USER_AGENT, _tls_context  # noqa: E402

DEST = ROOT / "app"
# Files every real export of this app has. Base44's export sometimes returns a stale starter
# template instead; without these, app/ is left untouched rather than overwritten with it.
MUST_HAVE = ("base44/functions/build-deck/entry.ts", "public/py/bundle.json", "src/routes/index.jsx")
SKIP = ("node_modules/", "dist/", ".wrangler/", ".output/", ".vinxi/", ".tanstack/", ".DS_Store")


def main() -> int:
    load_dotenv(ROOT / ".env")
    app_id, token = os.environ.get("BASE44_APP_ID"), os.environ.get("BASE44_TOKEN")
    if not (app_id and token):
        print("Set BASE44_APP_ID and BASE44_TOKEN in .env first.", file=sys.stderr)
        return 2
    req = request.Request(f"https://app.base44.com/api/apps/{app_id}/coding/export-to-zip",
                          headers={"Authorization": f"Bearer {token}", "User-Agent": USER_AGENT})
    with request.urlopen(req, context=_tls_context(), timeout=120) as resp:
        archive = zipfile.ZipFile(io.BytesIO(resp.read()))

    names = [n for n in archive.namelist() if not n.endswith("/")]
    # Strip a single top-level folder if the archive has one.
    prefix = os.path.commonprefix(names).rpartition("/")[0] + "/" if len({n.split("/")[0] for n in names}) == 1 else ""
    missing = [m for m in MUST_HAVE if prefix + m not in names]
    if missing:
        print(f"The export looks wrong (missing {', '.join(missing)}); app/ left as it was. Try again.",
              file=sys.stderr)
        return 1
    if DEST.exists():
        shutil.rmtree(DEST)
    written = 0
    for name in names:
        rel = name[len(prefix):]
        if not rel or any(part in rel for part in SKIP):
            continue
        out = DEST / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(archive.read(name))
        written += 1
    (DEST / "EXPORTED.json").write_text(json.dumps({
        "source": f"Base44 app {app_id}",
        "exported_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "files": written,
    }, indent=2) + "\n")
    print(f"Wrote {written} files to {DEST.relative_to(ROOT)}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
