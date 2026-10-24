import { createFileRoute } from "@tanstack/react-router";
import { useRef, useState } from "react";
import { Download, FileJson, Loader2, Upload } from "lucide-react";
import { runCasesFile } from "@/lib/pyodide";

export const Route = createFileRoute("/test")({
  ssr: false, // runs Python in the browser
  head: () => ({ meta: [{ title: "Test a file · Brightloop Pricing Watch" }] }),
  component: TestFile,
});

function TestFile() {
  const input = useRef(null);
  const [state, setState] = useState({ phase: "idle" });

  async function handle(file) {
    if (!file) return;
    setState({ phase: "running", name: file.name });
    try {
      const out = await runCasesFile(await file.text());
      setState({ phase: "done", name: file.name, ...out });
    } catch (err) {
      setState({ phase: "failed", name: file.name, message: err?.message || String(err) });
    }
  }

  function download() {
    const url = URL.createObjectURL(new Blob([state.text], { type: "application/json" }));
    const a = Object.assign(document.createElement("a"), { href: url, download: "result.json" });
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-3xl font-extrabold tracking-tight text-[#0F172A] md:text-4xl">Test a file</h1>
        <p className="mt-2 max-w-2xl text-[#64748B]">
          Upload a <span className="font-mono text-[#0F172A]">cases.json</span> and get back
          <span className="font-mono text-[#0F172A]"> result.json</span>. It runs the same Python code as
          <span className="font-mono text-[#0F172A]"> ./run --input cases.json --output result.json</span>, here in
          your browser. The file never leaves your computer.
        </p>
      </div>

      <div
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => { e.preventDefault(); handle(e.dataTransfer.files?.[0]); }}
        className="rounded-lg border-2 border-dashed border-[#E2E8F0] p-8 text-center md:p-12"
      >
        <FileJson className="mx-auto h-8 w-8 text-[#64748B]" />
        <p className="mt-3 font-semibold text-[#0F172A]">Drop cases.json here</p>
        <input ref={input} type="file" accept=".json,application/json,text/json,text/plain" className="hidden"
          onChange={(e) => { handle(e.target.files?.[0]); e.target.value = ""; }} />
        <button type="button" onClick={() => input.current?.click()} disabled={state.phase === "running"}
          className="mt-4 inline-flex min-h-[40px] items-center gap-2 rounded-lg bg-[#4F46E5] px-4 text-sm font-semibold text-white hover:bg-[#4338CA] disabled:opacity-60">
          <Upload className="h-4 w-4" /> Choose a file
        </button>
        {state.phase === "running" && (
          <p className="mt-4 inline-flex items-center gap-2 text-sm text-[#64748B]">
            <Loader2 className="h-4 w-4 animate-spin" />
            Running {state.name}. The first run loads the Python engine (about 10 MB), then it's instant.
          </p>
        )}
        {state.phase === "failed" && (
          <p className="mt-4 rounded-lg border border-[#E11D48]/30 bg-rose-50 p-3 text-sm text-[#9F1239]">{state.message}</p>
        )}
      </div>

      {state.phase === "done" && <Result state={state} onDownload={download} />}
    </div>
  );
}

function Result({ state, onDownload }) {
  const { result, name, sourceCommit } = state;
  const errors = result.run?.errors || [];
  return (
    <section className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4 rounded-lg border border-[#E2E8F0] bg-[#F8FAFC] p-5">
        <dl className="flex flex-wrap gap-x-8 gap-y-3 text-sm">
          <Stat label="File" value={name} />
          <Stat label="Built for" value={result.built_for} />
          <Stat label="Items" value={result.items.length} />
          <Stat label="Skipped" value={result.skipped.length} />
          <Stat label="Errors" value={errors.length} />
        </dl>
        <button type="button" onClick={onDownload}
          className="inline-flex min-h-[40px] items-center gap-2 rounded-lg border border-[#E2E8F0] bg-white px-4 text-sm font-semibold text-[#0F172A] hover:bg-[#F8FAFC]">
          <Download className="h-4 w-4" /> Download result.json
        </button>
      </div>

      {errors.length > 0 && (
        <ul className="space-y-2">
          {errors.map((e, i) => (
            <li key={i} className="rounded-lg border border-[#E11D48]/30 bg-rose-50 p-3 font-mono text-xs text-[#9F1239] break-words">{e}</li>
          ))}
        </ul>
      )}

      <div>
        <h2 className="font-display text-xl font-bold text-[#0F172A]">Items</h2>
        {result.items.length === 0 ? <p className="mt-2 text-[#64748B]">No pricing changes in this file.</p> : (
          <ul className="mt-3 space-y-3">
            {result.items.map((it) => (
              <li key={it.id} className="rounded-lg border border-[#E2E8F0] p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="font-mono text-xs text-[#64748B]">{it.id} · from {it.source_ids.join(", ")}</p>
                  <span className="rounded-md bg-[#EEF2FF] px-2 py-0.5 font-mono text-xs text-[#4F46E5]">
                    confidence {it.confidence}
                  </span>
                </div>
                <p className="mt-2 font-semibold text-[#0F172A]">{it.action}</p>
                <p className="mt-1 text-sm text-[#64748B]">{it.why}</p>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div>
        <h2 className="font-display text-xl font-bold text-[#0F172A]">Skipped</h2>
        {result.skipped.length === 0 ? <p className="mt-2 text-[#64748B]">Nothing skipped.</p> : (
          <ul className="mt-3 divide-y divide-[#E2E8F0] rounded-lg border border-[#E2E8F0]">
            {result.skipped.map((s) => (
              <li key={s.id} className="p-4">
                <p className="font-mono text-xs text-[#64748B]">{s.id}</p>
                <p className="mt-1 text-[#0F172A]">{s.reason}</p>
              </li>
            ))}
          </ul>
        )}
      </div>

      <p className="font-mono text-xs text-[#64748B]">Decision code from kfiralbase/brightloop@{sourceCommit}</p>
    </section>
  );
}

function Stat({ label, value }) {
  return (
    <div>
      <dt className="font-mono text-xs uppercase text-[#64748B]">{label}</dt>
      <dd className="mt-0.5 font-semibold text-[#0F172A] break-all">{value}</dd>
    </div>
  );
}
