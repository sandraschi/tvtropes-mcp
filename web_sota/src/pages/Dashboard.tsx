import { useCallback, useEffect, useState } from "react";
import {
  BookOpen,
  Globe,
  Layers,
  Lightbulb,
  Play,
  Square,
  RefreshCw,
  Search,
  ArrowRight,
  Loader2,
} from "lucide-react";
import { apiGet, apiPost } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { PageHero } from "@/components/layout/PageHero";

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

type CrawlResult = {
  success: boolean;
  starting_url: string;
  namespace: string;
  page_name: string;
  depth: number;
  pages_visited: number;
  urls_queued: number;
  error?: string;
};

export function Dashboard() {
  const [health, setHealth] = useState<Health | null>(null);
  const [status, setStatus] = useState<Status | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [scraperMsg, setScraperMsg] = useState<string | null>(null);

  const [crawlUrl, setCrawlUrl] = useState("Anime/Planetarian");
  const [crawlDepth, setCrawlDepth] = useState(1);
  const [crawlRunning, setCrawlRunning] = useState(false);
  const [crawlResult, setCrawlResult] = useState<CrawlResult | null>(null);
  const [crawlError, setCrawlError] = useState<string | null>(null);

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
      setErr(e instanceof Error ? e.message : String(e));
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

  const runCrawl = async () => {
    setCrawlRunning(true);
    setCrawlResult(null);
    setCrawlError(null);
    try {
      const r = await apiPost<CrawlResult>("/api/scraper/crawl", {
        url: crawlUrl,
        depth: crawlDepth,
      });
      setCrawlResult(r);
      if (!r.success) setCrawlError(r.error ?? "Crawl returned no result");
      fetchStatus();
    } catch (e) {
      setCrawlError(e instanceof Error ? e.message : "Crawl request failed");
    } finally {
      setCrawlRunning(false);
    }
  };

  const s = status?.scraper;

  return (
    <div className="space-y-8">
      <PageHero
        eyebrow="tvtropes-mcp"
        title="TVTropes local mirror"
        size="large"
        lead="Polite background crawler, Ollama extraction, 11 FastMCP tools, React dashboard, Calibre integration."
      />

      {err && (
        <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-2 text-sm">
          API: {err} — is the backend running on port 10964?
        </div>
      )}

      {/* Start a crawl card */}
      <Card>
        <CardTitle>
          <Search className="h-5 w-5 inline mr-2 text-primary" />
          Start a crawl from a URL
        </CardTitle>
        <p className="text-sm text-muted-foreground mt-1">
          Enter a TVTropes page path or URL to crawl it and linked pages up to the chosen depth.
        </p>
        <div className="flex flex-wrap gap-2 mt-3">
          <Input
            placeholder="Anime/Planetarian or full URL"
            value={crawlUrl}
            onChange={(e) => setCrawlUrl(e.target.value)}
            className="flex-1 min-w-[200px]"
          />
          <select
            value={crawlDepth}
            onChange={(e) => setCrawlDepth(Number(e.target.value))}
            className="h-10 rounded-md border border-input bg-background/60 px-3 text-sm"
          >
            {[1, 2, 3].map((d) => (
              <option key={d} value={d}>Depth {d}</option>
            ))}
          </select>
          <Button onClick={runCrawl} disabled={crawlRunning || !crawlUrl.trim()}>
            {crawlRunning ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <ArrowRight className="h-4 w-4 mr-1" />}
            Crawl
          </Button>
        </div>
        {crawlError && (
          <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-2 text-sm mt-2">
            {crawlError}
          </div>
        )}
        {crawlResult && crawlResult.success && (
          <div className="text-sm mt-2 space-y-1">
            <p>
              <span className="text-primary">{crawlResult.namespace}/{crawlResult.page_name}</span>
              {" — "}
              <span className="text-muted-foreground">
                {crawlResult.pages_visited} pages visited, {crawlResult.urls_queued} URLs queued
                {crawlResult.errors ? `, ${crawlResult.errors} blocked` : ""}
                {" (depth "}{crawlResult.depth}{")"}
              </span>
            </p>
            {crawlResult.note && (
              <p className="text-xs text-amber-400 mt-1">{crawlResult.note}</p>
            )}
          </div>
        )}
      </Card>

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

      {/* Scraper control */}
      <Card>
        <CardTitle>Background Scraper</CardTitle>
        <p className="text-sm text-muted-foreground mt-1">
          Full crawl bootstraps from the sitemap and runs for weeks at a polite 8–15s/page rate.
        </p>
        <div className="flex flex-wrap gap-2 mt-3">
          <Button size="sm" onClick={startScraper} disabled={s?.state === "running"}>
            <Play className="h-4 w-4 mr-1" /> Start
          </Button>
          <Button size="sm" variant="secondary" onClick={stopScraper} disabled={s?.state !== "running"}>
            <Square className="h-4 w-4 mr-1" /> Stop
          </Button>
        </div>
        {s && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-4 text-sm">
            <div><span className="text-muted-foreground">State</span><p className="font-medium">{s.state}</p></div>
            <div><span className="text-muted-foreground">Pending</span><p className="font-medium">{s.pending}</p></div>
            <div><span className="text-muted-foreground">Crawled</span><p className="font-medium">{s.crawled}</p></div>
            <div><span className="text-muted-foreground">Extracted</span><p className="font-medium">{s.extracted}</p></div>
            <div><span className="text-muted-foreground">Failed</span><p className="font-medium">{s.failed}</p></div>
            <div><span className="text-muted-foreground">Blocked</span><p className="font-medium">{s.blocked}</p></div>
            <div><span className="text-muted-foreground">Skipped</span><p className="font-medium">{s.skipped}</p></div>
            <div><span className="text-muted-foreground">Today</span><p className="font-medium">{s.daily}</p></div>
          </div>
        )}
        {scraperMsg && <p className="text-sm text-primary mt-2">{scraperMsg}</p>}
      </Card>

      <div>
        <h2 className="text-lg font-semibold tracking-tight">MCP Tools</h2>
        <p className="text-muted-foreground text-sm mt-1">11 tools registered via FastMCP 3.2.</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {[
          { label: "Trope Search", desc: "Full-text FTS5 search across indexed tropes.", icon: Lightbulb },
          { label: "Work Browser", desc: "Browse all tropes for films, series, books, games.", icon: BookOpen },
          { label: "Trope Graph", desc: "Traverse SubTrope, SuperTrope, SisterTrope.", icon: Layers },
          { label: "Namespaces", desc: "Filter by medium — Film, Anime, Literature, etc.", icon: Globe },
        ].map((t) => (
          <div key={t.label}>
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
