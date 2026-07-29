import { useCallback, useEffect, useState } from "react";
import { Calendar, Film, Loader2, Tv } from "lucide-react";
import { apiMcpTool } from "@/api/client";
import { PageHero } from "@/components/layout/PageHero";
import { Card, CardTitle } from "@/components/ui/card";

const RECENT_WORKS = [
  { ns: "Series", name: "Series", label: "TV Series" },
  { ns: "Anime", name: "Anime", label: "Anime" },
  { ns: "Film", name: "Film", label: "Film" },
];

type WorkEntry = { work_name: string; namespace: string };

export function CurrentSeason() {
  const [works, setWorks] = useState<Record<string, WorkEntry[]>>({});
  const [loading, setLoading] = useState(true);

  const fetch = useCallback(async () => {
    const results: Record<string, WorkEntry[]> = {};
    for (const ns of RECENT_WORKS) {
      try {
        const r = await apiMcpTool<{ success: boolean; works: WorkEntry[] }>(
          "works_in_namespace", { namespace: ns.name, limit: 20, offset: 0 }
        );
        results[ns.name] = r.works ?? [];
      } catch {
        results[ns.name] = [];
      }
    }
    setWorks(results);
    setLoading(false);
  }, []);

  useEffect(() => { fetch(); }, [fetch]);

  return (
    <div className="space-y-6">
      <PageHero
        eyebrow="Curated Page"
        title="What's in the Mirror"
        lead="Recently indexed works from the local TVTropes database — browse by medium to discover what's available."
      />

      {loading && (
        <div className="flex items-center gap-2 text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" /> Loading works...
        </div>
      )}

      {!loading && (
        <div className="grid gap-6 sm:grid-cols-3">
          {RECENT_WORKS.map((ns) => {
            const items = works[ns.name] ?? [];
            const Icon = ns.name === "Film" ? Film : ns.name === "Anime" ? Calendar : Tv;
            return (
              <div key={ns.name}>
                <CardTitle className="flex items-center gap-2 mb-3">
                  <Icon className="h-4 w-4 text-primary" />
                  {ns.label}
                  <span className="text-xs text-muted-foreground ml-auto">{items.length} works</span>
                </CardTitle>
                <Card>
                  {items.length === 0 ? (
                    <p className="text-xs text-muted-foreground p-3">No works indexed yet in this namespace.</p>
                  ) : (
                    <ul className="divide-y divide-border/40 text-sm max-h-[500px] overflow-y-auto">
                      {items.map((w) => (
                        <li key={w.work_name} className="px-3 py-1.5 hover:bg-muted/30 flex items-center gap-2">
                          <span className="w-1.5 h-1.5 rounded-full bg-primary/60 shrink-0" />
                          <span className="truncate">{w.work_name.replace(/([A-Z])/g, " $1").trim()}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </Card>
              </div>
            );
          })}
        </div>
      )}

      <div className="rounded-lg border border-muted/50 bg-muted/20 p-4">
        <p className="text-xs text-muted-foreground">
          These works are pulled from your local TVTropes mirror database.
          Works appear here after the scraper has indexed them.
        </p>
      </div>
    </div>
  );
}
