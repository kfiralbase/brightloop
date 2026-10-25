// Builds Maya's Monday deck in Google Slides, in the "Growth" folder of the connected Google Drive.
//
// Her layout, exactly: one slide per competitor (Lovable, Replit, Bolt); the homepage screenshot
// and the pricing-section screenshot, stacked or side by side, with the pricing shot getting about
// two thirds of the space; a red
// text box under the pricing shot only when something moved, nothing when it didn't. File name
// "Competitor Deck Wk of <Monday>". Re-running for the same week refills the same file.
// A site that didn't load keeps its slide with last week's pictures, marked "not checked" (Maya:
// "an empty slide just gets me questions I don't have answers to").
//
// Called by the weekly GitHub workflow after a run is published. Every function URL is public,
// so it requires the X-Deck-Secret header to match the DECK_SECRET app secret.
import { createClientFromRequest } from "npm:@base44/sdk";
import { secrets } from "base44:runtime";

const FOLDER = "Growth";
const ORDER = ["Lovable", "Replit", "Bolt"];
const EMU_PER_INCH = 914400;
const IN = (n: number) => Math.round(n * EMU_PER_INCH);
const RED = { red: 0.8, green: 0.1, blue: 0.1 };

type Box = { x: number; y: number; w: number; h: number };

function sameSecret(a: string, b: string): boolean {
  if (!a || !b || a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

const items = (res: any) => (Array.isArray(res) ? res : res?.items ?? []);

async function google(token: string, url: string, init: RequestInit = {}) {
  const res = await fetch(url, {
    ...init,
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json", ...(init.headers || {}) },
  });
  const body = res.status === 204 ? null : await res.json().catch(() => null);
  if (!res.ok) throw new Error(`${init.method || "GET"} ${url.split("?")[0]} → ${res.status}: ${JSON.stringify(body?.error?.message ?? body).slice(0, 300)}`);
  return body;
}

// Width and height from a PNG header, so the layout can keep each screenshot's shape.
async function pngSize(url: string): Promise<{ w: number; h: number } | null> {
  try {
    const res = await fetch(url, { headers: { Range: "bytes=0-31" } });
    const b = new Uint8Array(await res.arrayBuffer());
    if (b.length < 24) return null;
    const v = new DataView(b.buffer);
    return { w: v.getUint32(16), h: v.getUint32(20) };
  } catch {
    return null;
  }
}

function fit(img: { w: number; h: number }, box: Box): Box {
  const scale = Math.min(box.w / img.w, box.h / img.h);
  const w = img.w * scale, h = img.h * scale;
  return { x: box.x + (box.w - w) / 2, y: box.y, w, h };
}

// Stacked (homepage on top) or side by side (homepage left). The pricing shot is what leadership
// reads, so it gets about two thirds of the slide and the homepage, context only, about a third.
// With the real captures that's roughly 40-46% of the slide for pricing (was about 25% with an even
// split) while the homepage stays about 3 inches wide. Whichever arrangement shows pricing bigger wins.
const HOME_SHARES = [0.35];
const HOME_WEIGHT = 0.3;

function layout(home: { w: number; h: number }, pricing: { w: number; h: number }, area: Box, noteH: number) {
  const gap = IN(0.15);
  type L = { home: Box; pricing: Box; side: boolean };
  const options: L[] = [];
  for (const share of HOME_SHARES) {
    const homeH = (area.h - noteH - gap) * share;
    options.push({
      side: false,
      home: fit(home, { x: area.x, y: area.y, w: area.w, h: homeH }),
      pricing: fit(pricing, { x: area.x, y: area.y + homeH + gap, w: area.w, h: area.h - noteH - gap - homeH }),
    });
    const homeW = (area.w - gap) * share;
    options.push({
      side: true,
      home: fit(home, { x: area.x, y: area.y, w: homeW, h: area.h }),
      pricing: fit(pricing, { x: area.x + homeW + gap, y: area.y, w: area.w - gap - homeW, h: area.h - noteH }),
    });
  }
  const score = (l: L) => l.pricing.w * l.pricing.h + HOME_WEIGHT * l.home.w * l.home.h;
  const best = options.reduce((a, b) => (score(b) > score(a) ? b : a));
  if (!best.side) {
    // Stacked: keep the homepage directly above the pricing shot.
    best.pricing.y = best.home.y + best.home.h + gap;
    return best;
  }
  // Side by side: center the pair vertically, so the slide isn't top-heavy.
  const used = Math.max(best.home.h, best.pricing.h + noteH);
  const shift = Math.max(0, (area.h - used) / 2);
  best.home.y += shift + (used - best.home.h) / 2;
  best.pricing.y += shift;
  return best;
}

function image(id: string, slide: string, url: string, b: Box) {
  return {
    createImage: {
      objectId: id, url,
      elementProperties: {
        pageObjectId: slide,
        size: { width: { magnitude: Math.round(b.w), unit: "EMU" }, height: { magnitude: Math.round(b.h), unit: "EMU" } },
        transform: { scaleX: 1, scaleY: 1, translateX: Math.round(b.x), translateY: Math.round(b.y), unit: "EMU" },
      },
    },
  };
}

function textBox(id: string, slide: string, b: Box, text: string, style: Record<string, unknown>, outline = false) {
  const reqs: any[] = [
    {
      createShape: {
        objectId: id, shapeType: "TEXT_BOX",
        elementProperties: {
          pageObjectId: slide,
          size: { width: { magnitude: Math.round(b.w), unit: "EMU" }, height: { magnitude: Math.round(b.h), unit: "EMU" } },
          transform: { scaleX: 1, scaleY: 1, translateX: Math.round(b.x), translateY: Math.round(b.y), unit: "EMU" },
        },
      },
    },
    { insertText: { objectId: id, text } },
    { updateTextStyle: { objectId: id, style, fields: Object.keys(style).join(",") } },
  ];
  if (outline) {
    reqs.push({
      updateShapeProperties: {
        objectId: id, fields: "outline.outlineFill.solidFill.color,outline.weight",
        shapeProperties: { outline: { outlineFill: { solidFill: { color: { rgbColor: RED } } }, weight: { magnitude: 1.5, unit: "PT" } } },
      },
    });
  }
  return reqs;
}

// The deck a run feeds: the Monday on or after the run's date in Jerusalem. A Monday run feeds that
// day's deck; a Friday "Run now" feeds next Monday's. So a deck that leadership has already seen is
// never rewritten, and a change spotted midweek still reaches the next Monday's deck.
function jerusalemDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-CA", { timeZone: "Asia/Jerusalem" }); // YYYY-MM-DD
}

function deckMonday(iso: string): string {
  const day = jerusalemDate(iso);
  const d = new Date(`${day}T12:00:00Z`);
  const dow = d.getUTCDay(); // 0 Sunday .. 6 Saturday
  d.setUTCDate(d.getUTCDate() + ((8 - dow) % 7));
  return d.toISOString().slice(0, 10);
}

// Short, because the red box is "not a paragraph" (Maya): "(spotted Thu)".
function dayLabel(isoDay: string): string {
  return new Date(`${isoDay}T12:00:00Z`).toLocaleDateString("en-GB", { weekday: "short", timeZone: "UTC" });
}

function dayMonth(isoDay: string): string {
  const d = new Date(`${isoDay}T12:00:00Z`);
  return isNaN(d.getTime()) ? isoDay : d.toLocaleDateString("en-US", { month: "short", day: "numeric", timeZone: "UTC" });
}

function mondayLabel(weekOf: string): string {
  const d = new Date(`${weekOf}T12:00:00Z`);
  return isNaN(d.getTime()) ? weekOf : d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric", timeZone: "UTC" });
}

export default async function (req: Request): Promise<Response> {
  if (req.method !== "POST") return Response.json({ ok: false, error: "POST only" }, { status: 405 });
  if (!sameSecret(req.headers.get("x-deck-secret") || "", (await secrets.get("DECK_SECRET")) || "")) {
    return Response.json({ ok: false, error: "Unauthorized" }, { status: 401 });
  }
  const { run_key: runKey } = await req.json().catch(() => ({}));
  const sr = createClientFromRequest(req).asServiceRole;

  const run = runKey
    ? items(await sr.entities.Run.filter({ run_key: runKey }))[0]
    : items(await sr.entities.Run.filter({}, "-started_at", 1))[0];
  if (!run) return Response.json({ ok: false, error: `No run ${runKey || "(latest)"}` }, { status: 404 });

  try {
    const snaps = items(await sr.entities.Snapshot.filter({ run_key: run.run_key }));
    // Every change from every run that feeds this deck, not only this run's: a price spotted by a
    // Thursday "Run now" is gone from Monday's diff (the baseline already has it) but belongs here.
    const monday = deckMonday(run.started_at);
    const feeding = items(await sr.entities.Run.filter({}, "-started_at", 200))
      .filter((r: any) => r.started_at && deckMonday(r.started_at) === monday);
    const runDay = new Map(feeding.map((r: any) => [r.run_key, jerusalemDate(r.started_at)]));
    runDay.set(run.run_key, jerusalemDate(run.started_at));
    const today = jerusalemDate(run.started_at);
    const changes = items(await sr.entities.Change.filter({}, "-detected_at", 500))
      .filter((c: any) => runDay.has(c.run_key))
      .map((c: any) => ({
        ...c,
        deck_line: c.deck_line && runDay.get(c.run_key) !== today
          ? `${c.deck_line} (spotted ${dayLabel(runDay.get(c.run_key))})` : c.deck_line,
      }));
    if (!snaps.length) throw new Error("This run has no snapshots to put on slides.");
    // "Always Lovable, Replit, and Bolt in the deck": one with nothing captured yet still gets its slide.
    for (const c of ORDER) if (!snaps.some((s: any) => s.competitor === c)) snaps.push({ competitor: c, not_checked: true });
    snaps.sort((a: any, b: any) => (ORDER.indexOf(a.competitor) + 1 || 99) - (ORDER.indexOf(b.competitor) + 1 || 99));

    const drive = (await sr.connectors.getConnection("googledrive")).accessToken;
    const slidesTok = (await sr.connectors.getConnection("googleslides")).accessToken;
    const D = "https://www.googleapis.com/drive/v3/files";
    const q = (s: string) => `${D}?q=${encodeURIComponent(s)}&fields=files(id,name,webViewLink)&supportsAllDrives=true&includeItemsFromAllDrives=true`;

    const folders = (await google(drive, q(`mimeType='application/vnd.google-apps.folder' and name='${FOLDER}' and trashed=false`))).files;
    const folderId = folders[0]?.id
      ?? (await google(drive, `${D}?fields=id`, { method: "POST", body: JSON.stringify({ name: FOLDER, mimeType: "application/vnd.google-apps.folder" }) })).id;

    const name = `Competitor Deck Wk of ${mondayLabel(monday)}`;
    const existing = (await google(drive, q(`name='${name.replace(/'/g, "\\'")}' and '${folderId}' in parents and mimeType='application/vnd.google-apps.presentation' and trashed=false`))).files[0];
    const file = existing ?? await google(drive, `${D}?fields=id,webViewLink&supportsAllDrives=true`, {
      method: "POST", body: JSON.stringify({ name, mimeType: "application/vnd.google-apps.presentation", parents: [folderId] }),
    });

    const S = `https://slides.googleapis.com/v1/presentations/${file.id}`;
    const pres = await google(slidesTok, S);
    const oldSlides = (pres.slides || []).map((s: any) => s.objectId);
    const pageW = pres.pageSize.width.magnitude, pageH = pres.pageSize.height.magnitude;
    const margin = IN(0.3), titleH = IN(0.5);
    const tag = crypto.randomUUID().replace(/-/g, "").slice(0, 8);

    const requests: any[] = [];
    for (const [i, snap] of snaps.entries()) {
      const slide = `s${i}_${tag}`;
      requests.push({ createSlide: { objectId: slide, insertionIndex: i, slideLayoutReference: { predefinedLayout: "BLANK" } } });
      requests.push(...textBox(`t${i}_${tag}`, slide, { x: margin, y: margin * 0.6, w: pageW - 2 * margin, h: titleH },
        snap.competitor, { bold: true, fontSize: { magnitude: 20, unit: "PT" } }));

      // Warnings for Maya, top right: a site that didn't load, or screenshots the OCR check couldn't
      // match to the page text (the slide still goes in; she checks it before 11).
      const warnings: string[] = [];
      if (snap.not_checked) {
        const asOf = snap.fetched_at ? `screenshots from ${mondayLabel(snap.fetched_at.slice(0, 10))}` : "no earlier screenshots";
        warnings.push(`Not checked this week (site didn't load) · ${asOf}`);
      } else if (snap.verification_status === "mismatch") {
        warnings.push("Screenshot doesn't match the page text: check before 11");
      }
      if (warnings.length) {
        requests.push(...textBox(`x${i}_${tag}`, slide, { x: pageW / 2, y: margin * 0.6, w: pageW / 2 - margin, h: titleH },
          warnings.join("\n"),
          { bold: true, fontSize: { magnitude: 11, unit: "PT" }, foregroundColor: { opaqueColor: { rgbColor: RED } } }));
      }
      const lines = changes.filter((c: any) => c.competitor === snap.competitor).map((c: any) => c.deck_line).filter(Boolean);
      // The slide shows the monthly view, what loads by default. If only the annual price moved, it
      // shows the annual view instead, so the number in the red box is in the picture (Maya: "If only
      // the annual moved, I'd want to see that").
      const annualOnly = lines.length > 0 && lines.every((ln: string) => ln.includes("(annual)"));
      const pricingUrl = annualOnly && snap.annual_pricing_screenshot_url ? snap.annual_pricing_screenshot_url : snap.pricing_screenshot_url;
      if (pricingUrl && pricingUrl === snap.annual_pricing_screenshot_url && !warnings.length) {
        requests.push(...textBox(`a${i}_${tag}`, slide, { x: pageW / 2, y: margin * 0.6, w: pageW / 2 - margin, h: titleH },
          "Pricing shown in the annual billing view",
          { italic: true, fontSize: { magnitude: 11, unit: "PT" } }));
      }
      const noteH = lines.length ? IN(0.32) * lines.length + IN(0.15) : 0;
      const area = { x: margin, y: margin * 0.6 + titleH, w: pageW - 2 * margin, h: pageH - (margin * 0.6 + titleH) - margin * 0.6 };
      const [homeSize, priceSize] = await Promise.all([
        snap.homepage_screenshot_url ? pngSize(snap.homepage_screenshot_url) : null,
        pricingUrl ? pngSize(pricingUrl) : null,
      ]);
      const l = layout(homeSize || { w: 16, h: 10 }, priceSize || { w: 16, h: 9 }, area, noteH);
      const missing = { italic: true, fontSize: { magnitude: 12, unit: "PT" } };
      if (snap.homepage_screenshot_url) {
        requests.push(image(`h${i}_${tag}`, slide, snap.homepage_screenshot_url, l.home));
        // A bot check blocked this week's homepage, so last good picture is reused: say how old it is.
        const taken = (snap.homepage_captured_at || "").slice(0, 10), run = (snap.fetched_at || "").slice(0, 10);
        if (taken && run && taken !== run && !snap.not_checked) {
          // Short enough for one line under a homepage picture that's only about 3 inches wide.
          requests.push(...textBox(`c${i}_${tag}`, slide, { x: l.home.x, y: l.home.y + l.home.h + IN(0.03), w: l.home.w, h: IN(0.3) },
            `Homepage from ${dayMonth(taken)} (bot check this time)`,
            { italic: true, fontSize: { magnitude: 9, unit: "PT" } }));
        }
      } else {
        requests.push(...textBox(`h${i}_${tag}`, slide, l.home, "Homepage screenshot unavailable this week", missing));
      }
      if (pricingUrl) requests.push(image(`p${i}_${tag}`, slide, pricingUrl, l.pricing));
      else requests.push(...textBox(`p${i}_${tag}`, slide, l.pricing, "Pricing screenshot unavailable this week", missing));
      if (lines.length) {
        const note = { x: l.pricing.x, y: l.pricing.y + l.pricing.h + IN(0.08), w: Math.max(l.pricing.w, IN(3)), h: noteH - IN(0.08) };
        requests.push(...textBox(`n${i}_${tag}`, slide, note, lines.join("\n"),
          { bold: true, fontSize: { magnitude: 14, unit: "PT" }, foregroundColor: { opaqueColor: { rgbColor: RED } } }, true));
      }
    }
    // New slides first, then remove last week's (or the blank default), so the file is never empty.
    requests.push(...oldSlides.map((id: string) => ({ deleteObject: { objectId: id } })));
    await google(slidesTok, `${S}:batchUpdate`, { method: "POST", body: JSON.stringify({ requests }) });

    const deckUrl = file.webViewLink || `https://docs.google.com/presentation/d/${file.id}/edit`;
    // Clear a deck error left by an earlier failed attempt for this run.
    await sr.entities.Run.update(run.id, {
      deck_url: deckUrl,
      errors: (run.errors || []).filter((e: string) => !e.startsWith("Deck: ")),
    });
    // What's on the slides, for the Monday Slack message.
    const lines = changes.filter((c: any) => c.deck_line).map((c: any) => ({ competitor: c.competitor, deck_line: c.deck_line }));
    const notChecked = snaps.filter((s: any) => s.not_checked).map((s: any) => s.competitor);
    const unverified = snaps.filter((s: any) => !s.not_checked && s.verification_status === "mismatch").map((s: any) => s.competitor);
    return Response.json({ ok: true, deck_url: deckUrl, name, monday, slides: snaps.length, changes: changes.length,
      lines, not_checked: notChecked, unverified, reused: !!existing });
  } catch (err) {
    const message = `Deck: ${(err as Error).message}`;
    await sr.entities.Run.update(run.id, { errors: [...(run.errors || []).filter((e: string) => !e.startsWith("Deck: ")), message] }).catch(() => {});
    return Response.json({ ok: false, error: message }, { status: 500 });
  }
}
