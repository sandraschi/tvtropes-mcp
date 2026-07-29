import {
  ArrowRight,
  BookOpen,
  Globe,
  Layers,
  Lightbulb,
  Loader2,
  Play,
  Search,
  Square,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { apiGet, apiPost } from "@/api/client";
import { PageHero } from "@/components/layout/PageHero";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";

type Health = { status: string; service: string };
type ScraperInfo = {
  state: string;
  paused: boolean;
  pending: number;
  crawled: number;
  extracted: number;
  failed: number;
  skipped: number;
  blocked: number;
  daily: number;
  current_url: string;
  pages_crawled_this_session: number;
};
type Status = {
  scraper: ScraperInfo;
  extractor: { running: boolean };
  db: { size_mb: number; tropes: number; examples: number };
};

type CrawlResult = {
  success: boolean;
  starting_url: string;
  namespace: string;
  page_name: string;
  page_title?: string;
  depth: number;
  pages_visited: number;
  urls_queued: number;
  links_found?: number;
  errors?: number;
  error?: string;
  note?: string;
  sample_links?: { ns: string; name: string }[];
  next_steps?: string[];
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
      return true;
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
      return false;
    }
  }, []);

  const retryRef = useRef(0);
  useEffect(() => {
    let timer: ReturnType<typeof setTimeout> | undefined;
    const intervals = [1000, 2000, 4000, 8000, 16000];

    const poll = async () => {
      const ok = await fetchStatus();
      if (ok) {
        retryRef.current = 0;
        timer = setTimeout(poll, 10000);
      } else {
        const delay = intervals[Math.min(retryRef.current, intervals.length - 1)];
        retryRef.current += 1;
        timer = setTimeout(poll, delay);
      }
    };

    poll();

    // SSE for live updates (replaces polling for status refresh)
    let es: EventSource | undefined;
    try {
      es = new EventSource("/api/events");
      es.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data);
          setStatus((prev) => {
            if (!prev) return prev;
            return {
              ...prev,
              scraper: {
                ...prev.scraper,
                state: data.crawler_running ? "running" : "stopped",
                current_url: data.current_url ?? prev.scraper.current_url,
                crawled: data.crawled ?? prev.scraper.crawled,
                pending: data.pending ?? prev.scraper.pending,
                extracted: data.extracted ?? prev.scraper.extracted,
                daily: data.daily ?? prev.scraper.daily,
              },
              extractor: { running: data.extractor_running ?? prev.extractor?.running },
            };
          });
        } catch { /* ignore parse errors */ }
      };
    } catch { /* SSE not available */ }

    let unlisten: (() => void) | undefined;
    (async () => {
      try {
        const { listen } = await import("@tauri-apps/api/event");
        unlisten = await listen<string>("backend-status", (event) => {
          if (event.payload === "ready") fetchStatus();
          else if (typeof event.payload === "string" && event.payload.startsWith("error:")) setErr(event.payload);
        });
      } catch { /* not in Tauri */ }
    })();

    return () => {
      if (timer) clearTimeout(timer);
      if (es) es.close();
      if (unlisten) unlisten();
    };
  }, [fetchStatus]);

  const startScraper = async () => {
    setScraperMsg("Starting scraper...");
    try {
      const r = await apiPost<{ success: boolean; message: string }>("/api/scraper/start", {});
      setScraperMsg(r.message);
    } catch (e) {
      setScraperMsg(e instanceof Error ? e.message : "Failed");
    }
    setTimeout(() => setScraperMsg(null), 3000);
  };

  const stopScraper = async () => {
    setScraperMsg("Stopping scraper...");
    try {
      const r = await apiPost<{ success: boolean; message: string }>("/api/scraper/stop", {});
      setScraperMsg(r.message);
    } catch (e) {
      setScraperMsg(e instanceof Error ? e.message : "Failed");
    }
    setTimeout(() => setScraperMsg(null), 3000);
  };

  const pauseScraper = async () => {
    setScraperMsg("Pausing scraper...");
    try {
      const r = await apiPost<{ success: boolean; message: string }>("/api/scraper/pause", {});
      setScraperMsg(r.message);
    } catch (e) {
      setScraperMsg(e instanceof Error ? e.message : "Failed");
    }
    setTimeout(() => setScraperMsg(null), 3000);
  };

  const resumeScraper = async () => {
    setScraperMsg("Resuming scraper...");
    try {
      const r = await apiPost<{ success: boolean; message: string }>("/api/scraper/resume", {});
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
    <div className="space-y-8" data-testid="dashboard">
      <PageHero
        eyebrow="tvtropes-mcp"
        title="TVTropes crawler & search"
        lead="Background scraper that indexes tvtropes.org into a local SQLite database. Search tropes, browse by work/namespace, and navigate the trope relationship graph — no internet needed."
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
          Crawl a page to index it
        </CardTitle>
        <p className="text-sm text-muted-foreground mt-1">
          Pick a starting point below. The polite scraper fetches the page and follows links up to the chosen depth.
        </p>
        <div className="flex flex-wrap gap-2 mt-3">
          <select
            value={crawlUrl}
            onChange={(e) => setCrawlUrl(e.target.value)}
            className="flex-1 min-w-[200px] h-10 rounded-md border border-input bg-background/60 px-3 text-sm"
          >
            <option value="Anime/Planetarian">Anime/Planetarian</option>
            <option value="Film/JamesBond">Film/JamesBond</option>
            <option value="Anime/DetectiveConan">Anime/DetectiveConan</option>
            <option value="Theatre/WilliamShakespeare">Theatre/WilliamShakespeare</option>
            <option value="Main/TomatoInTheMirror">Main/TomatoInTheMirror</option>
            <option value="Film/TheMatrix">Film/TheMatrix</option>
            <option value="Series/BreakingBad">Series/BreakingBad</option>
            <option value="Literature/HarryPotter">Literature/HarryPotter</option>
            <option value="VideoGame/Portal">VideoGame/Portal</option>
            <option value="WesternAnimation/SpongeBobSquarePants">WesternAnimation/SpongeBobSquarePants</option>
            <option value="Music/TheBeatles">Music/TheBeatles</option>
          </select>
          <select
            value={crawlDepth}
            onChange={(e) => setCrawlDepth(Number(e.target.value))}
            className="h-10 rounded-md border border-input bg-background/60 px-3 text-sm"
          >
            {[1, 2, 3].map((d) => (
              <option key={d} value={d}>
                Depth {d}
              </option>
            ))}
          </select>
          <Button onClick={runCrawl} disabled={crawlRunning || !crawlUrl.trim()}>
            {crawlRunning ? (
              <Loader2 className="h-4 w-4 animate-spin mr-1" />
            ) : (
              <ArrowRight className="h-4 w-4 mr-1" />
            )}
            Crawl
          </Button>
        </div>
        {crawlError && (
          <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-2 text-sm mt-2">
            {crawlError}
          </div>
        )}
        {crawlResult?.success && (
          <div className="text-sm mt-2 space-y-2">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-primary font-medium">
                {crawlResult.page_title ?? `${crawlResult.namespace}/${crawlResult.page_name}`}
              </span>
              <span className="text-xs text-muted-foreground bg-muted/60 px-2 py-0.5 rounded">
                {crawlResult.namespace}/{crawlResult.page_name}
              </span>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
              <div>
                <span className="text-muted-foreground">Visited</span>
                <p className="font-medium">{crawlResult.pages_visited}</p>
              </div>
              <div>
                <span className="text-muted-foreground">Links found</span>
                <p className="font-medium">{crawlResult.links_found ?? 0}</p>
              </div>
              <div>
                <span className="text-muted-foreground">Queued</span>
                <p className="font-medium">{crawlResult.urls_queued}</p>
              </div>
              <div>
                <span className="text-muted-foreground">Depth</span>
                <p className="font-medium">{crawlResult.depth}</p>
              </div>
            </div>
            {crawlResult.sample_links && crawlResult.sample_links.length > 0 && (
              <div>
                <p className="text-xs text-muted-foreground mb-1">Sample linked pages:</p>
                <div className="flex flex-wrap gap-1">
                  {crawlResult.sample_links.map((l, i) => (
                    <span key={i} className="text-xs bg-muted/40 px-1.5 py-0.5 rounded">
                      {l.ns}/{l.name}
                    </span>
                  ))}
                </div>
              </div>
            )}
            {crawlResult.next_steps && crawlResult.next_steps.length > 0 && (
              <div className="text-xs text-green-400 space-y-0.5">
                {crawlResult.next_steps.map((s, i) => (
                  <p key={i}>{s}</p>
                ))}
              </div>
            )}
            {crawlResult.note && <p className="text-xs text-amber-400">{crawlResult.note}</p>}
          </div>
        )}
      </Card>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card data-testid="kpi-server">
          <CardTitle className="text-sm text-muted-foreground font-normal">API
            <span className="inline-block ml-2 w-2 h-2 rounded-full align-middle"
              data-testid="backend-dot"
              style={{ background: health ? "#22c55e" : err ? "#ef4444" : "#6b7280" }}
            />
          </CardTitle>
          <p className="text-2xl font-semibold mt-1">{health?.status ?? "…"}</p>
        </Card>
        <Card data-testid="kpi-tropes">
          <CardTitle className="text-sm text-muted-foreground font-normal">
            Tropes indexed
          </CardTitle>
          <p className="text-2xl font-semibold mt-1">{status?.db.tropes ?? "—"}</p>
        </Card>
        <Card data-testid="kpi-examples">
          <CardTitle className="text-sm text-muted-foreground font-normal">Examples</CardTitle>
          <p className="text-2xl font-semibold mt-1">{status?.db.examples ?? "—"}</p>
        </Card>
        <Card data-testid="kpi-dbsize">
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
          <Button size="sm" variant="outline" onClick={pauseScraper} disabled={s?.state !== "running" || s?.paused}>
            Pause
          </Button>
          <Button size="sm" variant="outline" onClick={resumeScraper} disabled={s?.state !== "running" || !s?.paused}>
            Resume
          </Button>
        </div>
        {s && (
          <div className="space-y-3 mt-4 text-sm">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              <div>
                <span className="text-muted-foreground">State</span>
                <p className="font-medium">{s.state}</p>
              </div>
              <div>
                <span className="text-muted-foreground">Extractor</span>
                <p className="font-medium">{status?.extractor?.running ? "running" : "idle"}</p>
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
              <div>
                <span className="text-muted-foreground">Session</span>
                <p className="font-medium">{s.pages_crawled_this_session ?? "—"}</p>
              </div>
            </div>
            {s.current_url && (
              <div className="rounded border border-primary/20 bg-primary/5 px-3 py-2">
                <p className="text-xs text-muted-foreground">Currently crawling</p>
                <p className="text-sm font-mono truncate" title={s.current_url}>{s.current_url}</p>
              </div>
            )}
          </div>
        )}
        {scraperMsg && <p className="text-sm text-primary mt-2">{scraperMsg}</p>}
      </Card>

      <div>
        <h2 className="text-lg font-semibold tracking-tight">MCP Tools</h2>
        <p className="text-muted-foreground text-sm mt-1">13 tools · 3 curated pages</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {[
          {
            label: "Trope Search",
            desc: "Full-text FTS5 search across indexed tropes.",
            icon: Lightbulb,
          },
          {
            label: "Work Browser",
            desc: "Browse all tropes for films, series, books, games.",
            icon: BookOpen,
          },
          {
            label: "Trope Graph",
            desc: "Traverse SubTrope, SuperTrope, SisterTrope.",
            icon: Layers,
          },
          {
            label: "Namespaces",
            desc: "Filter by medium — Film, Anime, Literature, etc.",
            icon: Globe,
          },
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
