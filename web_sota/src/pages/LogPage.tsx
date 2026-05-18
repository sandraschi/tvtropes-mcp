import { RefreshCw, Trash2 } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { apiGet } from "@/api/client";
import { PageHero } from "@/components/layout/PageHero";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type LogEntry = {
  ts: string;
  level: string;
  name: string;
  message: string;
};

export function LogPage() {
  const [entries, setEntries] = useState<LogEntry[]>([]);
  const [paused, setPaused] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  const fetchLogs = useCallback(async () => {
    try {
      const data = await apiGet<LogEntry[]>("/api/log?limit=200");
      setEntries(data);
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    fetchLogs();
    const interval = setInterval(() => {
      if (!paused) fetchLogs();
    }, 3000);
    return () => clearInterval(interval);
  }, [fetchLogs, paused]);

  useEffect(() => {
    if (!paused) endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [paused]);

  return (
    <div className="space-y-4">
      <PageHero
        eyebrow="Monitoring"
        title="Scraper Log"
        lead="Live log stream from the scraper daemon and MCP server. Polls the /api/log endpoint every 3s."
      >
        <div className="flex gap-2 pt-1">
          <Button size="sm" onClick={() => setPaused(!paused)}>
            {paused ? "Resume" : "Pause"}
          </Button>
          <Button size="sm" variant="outline" onClick={fetchLogs}>
            <RefreshCw className="h-4 w-4 mr-1" /> Refresh
          </Button>
          <Button size="sm" variant="ghost" onClick={() => setEntries([])}>
            <Trash2 className="h-4 w-4 mr-1" /> Clear
          </Button>
        </div>
      </PageHero>

      <div
        className="h-[60vh] overflow-y-auto font-mono text-xs space-y-0.5 bg-card/30 rounded-xl border border-border/60 p-3"
        onScroll={(e) => {
          const el = e.currentTarget;
          if (el.scrollHeight - el.scrollTop - el.clientHeight > 40) setPaused(true);
        }}
      >
        {entries.length === 0 && (
          <p className="text-muted-foreground text-center py-8">
            No log entries yet. Start the scraper to see output.
          </p>
        )}
        {entries.map((e, i) => (
          <div key={i} className="flex gap-2">
            <span className="text-muted-foreground shrink-0 w-8">
              {e.ts.split(" ")[1]?.slice(0, 8) ?? e.ts}
            </span>
            <span
              className={cn(
                "uppercase w-10 shrink-0",
                e.level === "error" && "text-red-400",
                e.level === "warn" && "text-amber-400",
                e.level === "debug" && "text-slate-400",
                e.level === "info" && "text-primary/80",
              )}
            >
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
