// Runs the repo's own Python (brightloop.file_run.run_file, the code behind `./run`) in the
// browser with Pyodide. public/py/bundle.json holds those modules, generated in the repo by
// scripts/browser_bundle.py; its source_commit says which commit they came from.
// Browser only: call from effects or event handlers, never during render.

const PYODIDE_URL = "https://cdn.jsdelivr.net/pyodide/v0.26.4/full/";

let engine = null;

function loadScript(src) {
  return new Promise((resolve, reject) => {
    if (window.loadPyodide) return resolve();
    const el = document.createElement("script");
    el.src = src;
    el.onload = () => resolve();
    el.onerror = () => reject(new Error("Couldn't load the Python engine. Check your connection and try again."));
    document.head.appendChild(el);
  });
}

export function loadEngine() {
  if (!engine) {
    engine = (async () => {
      await loadScript(`${PYODIDE_URL}pyodide.js`);
      const py = await window.loadPyodide({ indexURL: PYODIDE_URL });
      await py.loadPackage("tzdata"); // zoneinfo needs it for Asia/Jerusalem
      const res = await fetch("/py/bundle.json");
      if (!res.ok) throw new Error(`Couldn't load the decision code (HTTP ${res.status}).`);
      const bundle = await res.json();
      for (const [path, text] of Object.entries(bundle.files)) {
        py.FS.mkdirTree(`/app/${path.split("/").slice(0, -1).join("/")}`);
        py.FS.writeFile(`/app/${path}`, text);
      }
      py.runPython("import sys; sys.path.insert(0, '/app')");
      return { py, bundle };
    })().catch((err) => {
      engine = null; // let the next attempt start over
      throw err;
    });
  }
  return engine;
}

// cases.json text in, { result, text, sourceCommit } out. Same function as the CLI, so a
// broken file comes back as a result with run.errors, not as an exception.
export async function runCasesFile(fileText) {
  const { py, bundle } = await loadEngine();
  py.FS.writeFile("/tmp/cases.json", fileText);
  const text = py.runPython(`
import json
from brightloop.file_run import run_file
json.dumps(run_file("/tmp/cases.json"), indent=2, ensure_ascii=False)
`);
  return { result: JSON.parse(text), text: `${text}\n`, sourceCommit: bundle.source_commit };
}
