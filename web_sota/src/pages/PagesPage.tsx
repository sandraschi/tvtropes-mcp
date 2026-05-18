import { RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { apiGet } from "@/api/client";
import { PageHero } from "@/components/layout/PageHero";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

type PageRow = {
  id: number;
  url: string;
  namespace: string;
  page_name: string;
  status: string;
  crawled_at: string | null;
  http_status: number | null;
  blocked: boolean;
  retry_count: number;
};

type PagesResp = {
  total: number;
  pages: PageRow[];
  limit: number;
  offset: number;
};

type ContentResp = {
  url: string;
  content_hash: string;
  main_html: string;
  text: string;
  html_size: number;
  main_size: number;
  error?: string;
};

const STATUS_COLORS: Record<string, string> = {
  pending: "text-amber-400",
  crawling: "text-blue-400",
  crawled: "text-green-400",
  extracted: "text-green-300",
  failed: "text-red-400",
  skipped: "text-muted-foreground",
};

export function PagesPage() {
  const [data, setData] = useState<PagesResp | null>(null);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string | null>(null);
  const [nsFilter, setNsFilter] = useState("");
  const [selected, setSelected] = useState<PageRow | null>(null);
  const [content, setContent] = useState<ContentResp | null>(null);
  const [contentLoading, setContentLoading] = useState(false);
  const [viewMode, setViewMode] = useState<"html" | "text">("html");

  const fetchPages = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ limit: "50", offset: "0" });
      if (statusFilter) params.set("status", statusFilter);
      if (nsFilter.trim()) params.set("namespace", nsFilter.trim());
      const r = await apiGet<PagesResp>(`/api/pages?${params}`);
      setData(r);
    } catch {
      /* ignore */
    }
    setLoading(false);
  }, [statusFilter, nsFilter]);

  useEffect(() => {
    fetchPages();
  }, [fetchPages]);

  const openPage = useCallback(async (p: PageRow) => {
    setSelected(p);
    setContent(null);
    setContentLoading(true);
    try {
      const r = await apiGet<ContentResp>(`/api/pages/${p.id}/content`);
      setContent(r);
    } catch {
      /* ignore */
    }
    setContentLoading(false);
  }, []);

  const statuses = ["pending", "crawled", "extracted", "failed", "skipped"];

  return (
    <div className="space-y-4">
      <PageHero
        eyebrow="Browse"
        title="Crawled Pages"
        lead="Pages discovered and fetched by the scraper. Click a page to view its cached body content."
      >
        <div className="flex flex-wrap gap-2 pt-1">
          <Button
            size="sm"
            variant="ghost"
            onClick={() => {
              setStatusFilter(null);
              setNsFilter("");
            }}
          >
            All
          </Button>
          {statuses.map((s) => (
            <Button
              key={s}
              size="sm"
              variant={statusFilter === s ? "default" : "outline"}
              onClick={() => setStatusFilter(s === statusFilter ? null : s)}
            >
              {s}
            </Button>
          ))}
          <Button size="sm" variant="outline" onClick={fetchPages}>
            <RefreshCw className="h-4 w-4 mr-1" /> Refresh
          </Button>
        </div>
        <div className="flex gap-2 pt-1">
          <Input
            placeholder="Filter by namespace..."
            value={nsFilter}
            onChange={(e) => setNsFilter(e.target.value)}
            className="max-w-xs h-8 text-xs"
          />
        </div>
      </PageHero>

      <div className="grid gap-4 lg:grid-cols-2">
        {/* Page list */}
        <div className="space-y-2">
          {loading && <p className="text-sm text-muted-foreground">Loading...</p>}
          {data && (
            <p className="text-xs text-muted-foreground">
              {data.total} pages
              {data.pages.length < data.total && ` (showing ${data.pages.length})`}
            </p>
          )}
          {data?.pages.map((p) => (
            <button
              key={p.id}
              onClick={() => openPage(p)}
              className={cn(
                "w-full text-left",
                "rounded-lg border p-2 transition-colors text-xs",
                selected?.id === p.id
                  ? "border-primary bg-primary/5"
                  : "border-border hover:border-primary/40 bg-card/30",
              )}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-medium truncate">
                  {p.namespace}/{p.page_name}
                </span>
                <span className={cn("shrink-0", STATUS_COLORS[p.status] ?? "")}>{p.status}</span>
              </div>
              <div className="flex gap-3 text-muted-foreground mt-0.5">
                {p.http_status && <span>HTTP {p.http_status}</span>}
                {p.crawled_at && <span>{p.crawled_at}</span>}
                {p.blocked && <span className="text-amber-400">blocked</span>}
              </div>
            </button>
          ))}
          {data?.pages.length === 0 && (
            <p className="text-sm text-muted-foreground text-center py-8">
              No pages found. Start a crawl from the Dashboard.
            </p>
          )}
        </div>

        {/* Page content */}
        <div className="space-y-2">
          {selected && (
            <div className="flex items-center justify-between gap-2 mb-2">
              <div className="text-sm font-medium truncate">
                {selected.namespace}/{selected.page_name}
              </div>
              <div className="flex gap-1">
                <Button
                  size="sm"
                  variant={viewMode === "html" ? "default" : "ghost"}
                  className="h-7 text-xs"
                  onClick={() => setViewMode("html")}
                >
                  HTML
                </Button>
                <Button
                  size="sm"
                  variant={viewMode === "text" ? "default" : "ghost"}
                  className="h-7 text-xs"
                  onClick={() => setViewMode("text")}
                >
                  Text
                </Button>
              </div>
            </div>
          )}

          {contentLoading && (
            <div className="flex items-center justify-center py-12">
              <RefreshCw className="h-6 w-6 animate-spin text-primary" />
            </div>
          )}

          {content?.error && (
            <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-2 text-sm">
              {content.error}
            </div>
          )}

          {content && !content.error && (
            <Card>
              <div className="text-xs text-muted-foreground mb-2 flex gap-3">
                <span>{content.html_size.toLocaleString()} bytes raw</span>
                <span>{content.main_size.toLocaleString()} bytes extracted</span>
              </div>
              <div className="max-h-[60vh] overflow-y-auto">
                {viewMode === "html" ? (
                  <div
                    className="prose prose-xs prose-invert max-w-none [&_a]:text-primary [&_a]:hover:underline"
                    dangerouslySetInnerHTML={{ __html: content.main_html }}
                  />
                ) : (
                  <pre className="text-xs whitespace-pre-wrap font-sans leading-relaxed">
                    {content.text}
                  </pre>
                )}
              </div>
            </Card>
          )}

          {!selected && !contentLoading && (
            <p className="text-sm text-muted-foreground text-center py-12">
              Select a page from the list to view its cached content.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
