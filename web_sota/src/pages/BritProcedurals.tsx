import { useCallback, useEffect, useState } from "react";
import { Loader2, Shield } from "lucide-react";
import { apiMcpTool } from "@/api/client";
import { PageHero } from "@/components/layout/PageHero";
import { Card, CardTitle } from "@/components/ui/card";

const BRIT_PROCEDURALS = [
  { id: "Series/Broadchurch", label: "Broadchurch" },
  { id: "Series/LineOfDuty", label: "Line of Duty" },
  { id: "Series/Sherlock", label: "Sherlock" },
  { id: "Series/MidsomerMurders", label: "Midsomer Murders" },
  { id: "Series/PrimeSuspect", label: "Prime Suspect" },
  { id: "Series/Luther", label: "Luther" },
  { id: "Series/InspectorMorse", label: "Inspector Morse" },
  { id: "Series/HappyValley", label: "Happy Valley" },
  { id: "Series/Vera", label: "Vera" },
  { id: "Series/Shetland", label: "Shetland" },
  { id: "Series/WireInTheBlood", label: "Wire in the Blood" },
  { id: "Series/Cracker", label: "Cracker" },
  { id: "Series/FoyleSWar", label: "Foyle's War" },
  { id: "Series/TheBill", label: "The Bill" },
  { id: "Series/SilentWitness", label: "Silent Witness" },
];

type ShowResult = {
  id: string;
  label: string;
  tropes: { trope_ns: string; trope_name: string; title: string }[];
  count: number;
  error?: string;
};

export function BritProcedurals() {
  const [shows, setShows] = useState<ShowResult[]>([]);
  const [loading, setLoading] = useState(true);

  const fetch = useCallback(async () => {
    const results: ShowResult[] = [];
    for (const show of BRIT_PROCEDURALS) {
      try {
        const r = await apiMcpTool<{ success: boolean; tropes: { trope_ns: string; trope_name: string; title: string }[] }>(
          "work_tropes", { work_id: show.id }
        );
        results.push({ ...show, tropes: r.tropes ?? [], count: r.tropes?.length ?? 0 });
      } catch {
        results.push({ ...show, tropes: [], count: 0, error: "Not in mirror yet" });
      }
    }
    setShows(results);
    setLoading(false);
  }, []);

  useEffect(() => { fetch(); }, [fetch]);

  const present = shows.filter((s) => s.count > 0);
  const absent = shows.filter((s) => s.count === 0);

  return (
    <div className="space-y-6">
      <PageHero
        eyebrow="Curated Page"
        title="British Police Procedurals"
        lead="From Midsomer to Shetland — tropes that define British crime drama, pulled from the local TVTropes mirror."
      />

      {loading && (
        <div className="flex items-center gap-2 text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" /> Loading shows...
        </div>
      )}

      {!loading && present.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {present.sort((a, b) => b.count - a.count).map((show) => (
            <Card key={show.id} className="h-full">
              <CardTitle className="flex items-center gap-2">
                <Shield className="h-4 w-4 text-primary shrink-0" />
                {show.label}
              </CardTitle>
              <p className="text-xs text-muted-foreground mt-1">{show.count} tropes indexed</p>
              <div className="flex flex-wrap gap-1 mt-2">
                {show.tropes.slice(0, 8).map((t) => (
                  <span key={t.trope_name} className="text-xs bg-muted/60 px-1.5 py-0.5 rounded">
                    {t.title || t.trope_name}
                  </span>
                ))}
                {show.count > 8 && (
                  <span className="text-xs text-muted-foreground">+{show.count - 8} more</span>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}

      {!loading && absent.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-muted-foreground mb-2">
            Not yet in the mirror ({absent.length})
          </h3>
          <div className="flex flex-wrap gap-2">
            {absent.map((s) => (
              <span key={s.id} className="text-xs bg-muted/30 px-2 py-1 rounded text-muted-foreground">
                {s.label}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
