import { useEffect, useState } from "react";
import { BookOpen, Globe, Layers, Lightbulb } from "lucide-react";
import { apiGet } from "@/api/client";
import { Card, CardTitle } from "@/components/ui/card";

type Health = { status: string; service: string };
type Status = {
  scraper: { state: string; pages_visited: number; pages_queued: number };
  db: { size_mb: number; tropes: number; examples: number };
  ollama: { queue_depth: number; avg_latency_ms: number };
};

export function Dashboard() {
  const [health, setHealth] = useState<Health | null>(null);
  const [status, setStatus] = useState<Status | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [h, s] = await Promise.all([
          apiGet<Health>("/api/health"),
          apiGet<Status>("/api/status"),
        ]);
        if (!cancelled) {
          setHealth(h);
          setStatus(s);
        }
      } catch (e) {
        const m = e instanceof Error ? e.message : String(e);
        if (!cancelled) setErr(m);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const tiles = [
    {
      label: "Trope Search",
      desc: "Full-text search across 200K+ tropes and their descriptions.",
      icon: Lightbulb,
    },
    {
      label: "Work Browser",
      desc: "Browse all tropes for films, series, books, games, and more.",
      icon: BookOpen,
    },
    {
      label: "Trope Graph",
      desc: "Traverse SubTrope / SuperTrope / SisterTrope relationships.",
      icon: Layers,
    },
    {
      label: "Namespaces",
      desc: "Filter by medium — Film, Literature, Anime, VideoGame, and more.",
      icon: Globe,
    },
  ];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">TVTropes MCP</h1>
        <p className="text-muted-foreground mt-2 max-w-2xl">
          Local mirror of the TVTropes knowledge graph. Background scraper builds a SQLite database;
          MCP tools query it without touching the network. Dashboard shows scraper progress and DB
          stats.
        </p>
      </div>

      {err && (
        <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-2 text-sm">
          API: {err} — is the backend running on <code>10964</code>?
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardTitle className="text-sm text-muted-foreground font-normal">API</CardTitle>
          <p className="text-2xl font-semibold mt-1">{health?.status ?? "…"}</p>
        </Card>
        <Card>
          <CardTitle className="text-sm text-muted-foreground font-normal">Tropes indexed</CardTitle>
          <p className="text-2xl font-semibold mt-1">{status?.db.tropes ?? "—"}</p>
        </Card>
        <Card>
          <CardTitle className="text-sm text-muted-foreground font-normal">Examples</CardTitle>
          <p className="text-2xl font-semibold mt-1">{status?.db.examples ?? "—"}</p>
        </Card>
        <Card>
          <CardTitle className="text-sm text-muted-foreground font-normal">DB Size</CardTitle>
          <p className="text-2xl font-semibold mt-1">
            {status ? `${status.db.size_mb.toFixed(1)} MB` : "—"}
          </p>
        </Card>
      </div>

      <div>
        <h2 className="text-lg font-semibold tracking-tight">MCP Tools</h2>
        <p className="text-muted-foreground text-sm mt-1">
          8 tools registered via FastMCP 3.2. All return stubs until the scraper is implemented.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {tiles.map((t) => (
          <div key={t.label} className="block group">
            <Card className="h-full">
              <div className="flex gap-3">
                <t.icon className="h-8 w-8 text-primary shrink-0" />
                <div>
                  <CardTitle>{t.label}</CardTitle>
                  <p className="text-sm text-muted-foreground mt-1 leading-snug">{t.desc}</p>
                </div>
              </div>
            </Card>
          </div>
        ))}
      </div>

      <Card>
        <CardTitle>Scraper Status</CardTitle>
        <p className="text-sm text-muted-foreground mt-1">
          {status?.scraper.state === "not_started"
            ? "Scraper not yet started. See docs/SCRAPER_PLAN.md for the 4-phase implementation plan."
            : `Crawling: ${status?.scraper.pages_visited ?? 0} pages visited, ${status?.scraper.pages_queued ?? 0} queued.`}
        </p>
      </Card>
    </div>
  );
}
