import { createFileRoute } from "@tanstack/react-router";
import { secrets } from "base44:runtime";
import { requireUserRoute } from "@/lib/auth-middleware";

// Called by the "Monday pricing run" workflow. The workflow calls as the app's admin creator;
// anonymous callers get 401 from the middleware and non-admins get 403.
const DISPATCH_URL = "https://api.github.com/repos/kfiralbase/brightloop/actions/workflows/weekly.yml/dispatches";

export const Route = createFileRoute("/api/start-weekly")({
  server: {
    middleware: [requireUserRoute],
    handlers: {
      POST: async ({ context }) => {
        if (context.user.role !== "admin") return Response.json({ ok: false, error: "Forbidden" }, { status: 403 });
        const token = await secrets.get("GITHUB_TOKEN");
        if (!token) return Response.json({ ok: false, status: 500, error: "GITHUB_TOKEN is not set" }, { status: 500 });
        const res = await fetch(DISPATCH_URL, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
            Accept: "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "brightloop-pricing-watch",
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ ref: "main", inputs: { notify: "true" } }),
        });
        if (res.status === 204) return Response.json({ ok: true });
        const body = await res.json().catch(() => null);
        const error = body?.message || `GitHub answered ${res.status}`;
        // Non-2xx so the workflow step (and run) is marked failed.
        return Response.json({ ok: false, status: res.status, error }, { status: 502 });
      },
    },
  },
});