import { useCallback, useEffect, useRef, useState } from "react";
import { Download, Pause, Play, RefreshCw, Trash2 } from "lucide-react";
import { apiGet } from "@/api/client";
import { Button } from "@/components/ui/button";
import { PageHero } from "@/components/layout/PageHero";
import { cn } from "@/lib/utils";

type LogEntry = { ts: string; level: string; name: string; message: string };
type LogResp = { entries: LogEntry[]; total: number };

const LEVELS = ["all", "info", "warn", "error", "debug"] as const;
type Level = (typeof LEVELS)[number];

const LEVEL_COLORS: Record<string, string> = {
  error: "text-red-400",
  warn: "text-amber-400",
  debug: "text-slate-400",
  info: "text-primary/80",
};

export function LogPage() {
  const [entries, setEntries] = useState<LogEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [paused, setPaused] = useState(false);
  const [level, setLevel] = useState<Level>("all");
  const endRef = useRef<HTMLDivElement>(null);

  const fetchLogs = useCallback(async () => {
    try {
      const params = new URLSearchParams({ limit: "200" });
      if (level !== "all") params.set("level", level);
      const data = await apiGet<LogResp>(`/api/log?${params}`);
      setEntries(data.entries);
      setTotal(data.total);
    } catch { /* ignore */ }
  }, [level]);

  useEffect(() => {
    fetchLogs();
    const interval = setInterval(() => {
      if (!paused) fetchLogs();
    }, 3000);
    return () => clearInterval(interval);
  }, [fetchLogs, paused]);

  useEffect(() => {
    if (!paused) endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [entries, paused]);

  const exportLogs = async () => {
    try {
      const data = await apiGet<{ exported: number; entries: LogEntry[] }>("/api/log/export");
      const csvRows = [
        ["timestamp", "level", "module", "message"].join(","),
        ...data.entries.map((e) =>
          [e.ts, e.level.toUpperCase(), (e.name ?? "").split(".").slice(-1)[0] ?? "", `"${(e.message ?? "").replace(/"/g, '""')}"`].join(","),
        ),
      ];
      const text = csvRows.join("\n");
      const blob = new Blob([text], { type: "text/csv;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `tvtropes-log-${new Date().toISOString().slice(0, 19).replace(/:/g, "-")}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } catch { /* ignore */ }
  };

  const togglePause = () => setPaused(!paused);

  return (
    <div className="space-y-4">
      <PageHero
        eyebrow="Monitoring"
        title="Scraper Log"
        lead={`Live log stream from the scraper daemon and MCP server. Polls every 3s. ${total} entries matching filter.`}
      >
        <div className="flex flex-wrap gap-2 pt-1">
          <Button size="sm" onClick={togglePause}>
            {paused ? <Play className="h-4 w-4 mr-1" /> : <Pause className="h-4 w-4 mr-1" />}
            {paused ? "Resume" : "Pause"}
          </Button>
          <Button size="sm" variant="outline" onClick={fetchLogs}>
            <RefreshCw className="h-4 w-4 mr-1" /> Refresh
          </Button>
          <Button size="sm" variant="outline" onClick={exportLogs}>
            <Download className="h-4 w-4 mr-1" /> Export CSV
          </Button>
          <Button size="sm" variant="ghost" onClick={() => setEntries([])}>
            <Trash2 className="h-4 w-4 mr-1" /> Clear
          </Button>
        </div>
      </PageHero>

      {/* Level filters */}
      <div className="flex flex-wrap gap-1.5">
        {LEVELS.map((l) => (
          <button
            key={l}
            type="button"
            onClick={() => setLevel(l)}
            className={cn(
              "text-xs px-3 py-1 rounded-full border transition-colors",
              level === l
                ? "bg-primary text-primary-foreground border-primary"
                : "border-border hover:border-primary/40 text-muted-foreground",
              l === "error" && level === l && "bg-red-600 border-red-600",
              l === "warn" && level === l && "bg-amber-600 border-amber-600",
            )}
          >
            {l === "all" ? "All" : l.toUpperCase()}
          </button>
        ))}
      </div>

      {/* Log entries */}
      <div
        className="h-[60vh] overflow-y-auto font-mono text-xs space-y-0.5 bg-card/30 rounded-xl border border-border/60 p-3"
        onScroll={(e) => {
          const el = e.currentTarget;
          if (el.scrollHeight - el.scrollTop - el.clientHeight > 40) setPaused(true);
        }}
      >
        {entries.length === 0 && (
          <p className="text-muted-foreground text-center py-8">
            {level !== "all"
              ? `No ${level.toUpperCase()} log entries. Try a different filter.`
              : "No log entries yet. Start the scraper to see output."}
          </p>
        )}
        {entries.map((e, i) => (
          <div key={i} className="flex gap-2 hover:bg-muted/20 rounded-sm">
            <span className="text-muted-foreground shrink-0 w-20">{e.ts}</span>
            <span className={cn("uppercase w-10 shrink-0 font-medium", LEVEL_COLORS[e.level] ?? "")}>
              {e.level}
            </span>
            <span className="text-muted-foreground shrink-0 w-20 truncate">
              {e.name?.split(".").slice(-1)[0] ?? "—"}
            </span>
            <span className="break-all">{e.message}</span>
          </div>
        ))}
        <div ref={endRef} />
      </div>
    </div>
  );
}
