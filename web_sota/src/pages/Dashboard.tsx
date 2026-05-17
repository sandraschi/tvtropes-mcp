import { useCallback, useEffect, useState } from "react";
import {
  BookOpen,
  Globe,
  Layers,
  Lightbulb,
  Play,
  Square,
  RefreshCw,
} from "lucide-react";
import { apiGet, apiPost } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";

type Health = { status: string; service: string };
type ScraperInfo = {
  state: string;
  pending: number;
  crawled: number;
  extracted: number;
  failed: number;
  skipped: number;
  blocked: number;
  daily: number;
};
type Status = {
  scraper: ScraperInfo;
  db: { size_mb: number; tropes: number; examples: number };
};

export function Dashboard() {
  const [health, setHealth] = useState<Health | null>(null);
  const [status, setStatus] = useState<Status | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [scraperMsg, setScraperMsg] = useState<string | null>(null);

  const fetchStatus = useCallback(async () => {
    try {
      const [h, s] = await Promise.all([
        apiGet<Health>("/api/health"),
        apiGet<Status>("/api/status"),
      ]);
      setHealth(h);
      setStatus(s);
      setErr(null);
    } catch (e) {
      const m = e instanceof Error ? e.message : String(e);
      setErr(m);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 10000);
    return () => clearInterval(interval);
  }, [fetchStatus]);

  const startScraper = async () => {
    setScraperMsg("Starting scraper...");
    try {
      const r = await apiPost<{ success: boolean; message: string }>("/api/scraper/start");
      setScraperMsg(r.message);
    } catch (e) {
      setScraperMsg(e instanceof Error ? e.message : "Failed");
    }
    setTimeout(() => setScraperMsg(null), 3000);
  };

  const stopScraper = async () => {
    setScraperMsg("Stopping scraper...");
    try {
      const r = await apiPost<{ success: boolean; message: string }>("/api/scraper/stop");
      setScraperMsg(r.message);
    } catch (e) {
      setScraperMsg(e instanceof Error ? e.message : "Failed");
    }
    setTimeout(() => setScraperMsg(null), 3000);
  };

  const runExtraction = async () => {
    setScraperMsg("Running extraction pass...");
    try {
      const r = await apiPost<{ success: boolean; extracted: number }>("/api/scraper/extract");
      setScraperMsg(`Extraction pass done: ${r.extracted} pages`);
      fetchStatus();
    } catch (e) {
      setScraperMsg(e instanceof Error ? e.message : "Failed");
    }
    setTimeout(() => setScraperMsg(null), 5000);
  };

  const s = status?.scraper;

  const tiles = [
    {
      label: "Trope Search",
      desc: "Full-text search across indexed tropes using SQLite FTS5.",
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
          Local mirror of the TVTropes knowledge graph. Background scraper builds a SQLite
          database using curl_cffi (Chrome TLS bypass) + Ollama extraction. MCP tools query it
          without touching the network.
        </p>
      </div>

      {err && (
        <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-2 text-sm">
          API: {err} — is the backend running on port 10964?
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

      <Card>
        <CardTitle>Scraper Control</CardTitle>
        <div className="flex flex-wrap gap-2 mt-3">
          <Button
            size="sm"
            onClick={startScraper}
            disabled={s?.state === "running"}
          >
            <Play className="h-4 w-4 mr-1" />
            Start
          </Button>
          <Button
            size="sm"
            variant="secondary"
            onClick={stopScraper}
            disabled={s?.state !== "running"}
          >
            <Square className="h-4 w-4 mr-1" />
            Stop
          </Button>
          <Button size="sm" variant="outline" onClick={runExtraction}>
            <RefreshCw className="h-4 w-4 mr-1" />
            Extract Pass
          </Button>
        </div>
        {s && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-4 text-sm">
            <div>
              <span className="text-muted-foreground">State</span>
              <p className="font-medium">{s.state}</p>
            </div>
            <div>
              <span className="text-muted-foreground">Pending</span>
              <p className="font-medium">{s.pending}</p>
            </div>
            <div>
              <span className="text-muted-foreground">Crawled</span>
              <p className="font-medium">{s.crawled}</p>
            </div>
            <div>
              <span className="text-muted-foreground">Extracted</span>
              <p className="font-medium">{s.extracted}</p>
            </div>
            <div>
              <span className="text-muted-foreground">Failed</span>
              <p className="font-medium">{s.failed}</p>
            </div>
            <div>
              <span className="text-muted-foreground">Blocked</span>
              <p className="font-medium">{s.blocked}</p>
            </div>
            <div>
              <span className="text-muted-foreground">Skipped</span>
              <p className="font-medium">{s.skipped}</p>
            </div>
            <div>
              <span className="text-muted-foreground">Today</span>
              <p className="font-medium">{s.daily}</p>
            </div>
          </div>
        )}
        {scraperMsg && (
          <p className="text-sm text-primary mt-2">{scraperMsg}</p>
        )}
      </Card>

      <div>
        <h2 className="text-lg font-semibold tracking-tight">MCP Tools</h2>
        <p className="text-muted-foreground text-sm mt-1">
          8 tools registered via FastMCP 3.2. Query the DB or control the scraper.
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
    </div>
  );
}
