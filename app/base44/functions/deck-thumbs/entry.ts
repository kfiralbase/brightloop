// Temporary QA helper: returns thumbnail URLs for a deck's slides. Same secret as build-deck.
import { createClientFromRequest } from "npm:@base44/sdk";
import { secrets } from "base44:runtime";

export default async function (req: Request): Promise<Response> {
  if (req.headers.get("x-deck-secret") !== (await secrets.get("DECK_SECRET"))) {
    return Response.json({ ok: false }, { status: 401 });
  }
  const { presentation_id: id } = await req.json();
  const tok = (await createClientFromRequest(req).asServiceRole.connectors.getConnection("googleslides")).accessToken;
  const h = { Authorization: `Bearer ${tok}` };
  const pres = await (await fetch(`https://slides.googleapis.com/v1/presentations/${id}?fields=slides.objectId`, { headers: h })).json();
  const thumbs = [];
  for (const s of pres.slides || []) {
    const t = await (await fetch(`https://slides.googleapis.com/v1/presentations/${id}/pages/${s.objectId}/thumbnail?thumbnailProperties.thumbnailSize=LARGE`, { headers: h })).json();
    thumbs.push(t.contentUrl);
  }
  return Response.json({ ok: true, thumbs });
}
