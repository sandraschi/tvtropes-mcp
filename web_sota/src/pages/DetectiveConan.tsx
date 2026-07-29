import { useCallback, useEffect, useState } from "react";
import { Loader2, Star } from "lucide-react";
import { apiMcpTool } from "@/api/client";
import { PageHero } from "@/components/layout/PageHero";
import { Card, CardTitle } from "@/components/ui/card";

type TropeInfo = {
  id: string;
  name: string;
  description: string;
  examples: { work_ns: string; work_name: string; example_text: string }[];
  sub_tropes: { namespace: string; page_name: string }[];
  super_tropes: { namespace: string; page_name: string }[];
};

export function DetectiveConan() {
  const [tropes, setTropes] = useState<TropeInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    setLoading(true);
    try {
      const result = await apiMcpTool<{ success: boolean; tropes: { trope_ns: string; trope_name: string; title: string }[] }>(
        "work_tropes", { work_id: "Anime/DetectiveConan" }
      );
      if (!result.success || !result.tropes) {
        setTropes([]);
        setLoading(false);
        return;
      }
      const names = result.tropes.slice(0, 30);
      const details: TropeInfo[] = [];
      for (const t of names) {
        const full = await apiMcpTool<{ success: boolean; trope: TropeInfo | null }>(
          "trope_get", { trope_id: `${t.trope_ns}/${t.trope_name}` }
        );
        if (full.success && full.trope) details.push(full.trope);
      }
      setTropes(details);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
    setLoading(false);
  }, []);

  useEffect(() => { fetch(); }, [fetch]);

  return (
    <div className="space-y-6">
      <PageHero
        eyebrow="Curated Page"
        title="Detective Conan"
        lead="The world's greatest detective trapped in a child's body — tropes, examples, and relations from the TVTropes mirror."
      />

      {loading && (
        <div className="flex items-center gap-2 text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" /> Loading tropes...
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-2 text-sm">{error}</div>
      )}

      {!loading && !error && tropes.length === 0 && (
        <div className="rounded-lg border border-muted px-4 py-6 text-center text-muted-foreground">
          No tropes found for Detective Conan in the local mirror. The scraper may not have reached it yet.
        </div>
      )}

      {tropes.length > 0 && (
        <div className="grid gap-3 sm:grid-cols-2">
          {tropes.map((t) => (
            <Card key={t.id} className="group">
              <CardTitle className="flex items-center gap-2 text-sm">
                <Star className="h-4 w-4 text-primary shrink-0" />
                {t.name}
              </CardTitle>
              {t.description && (
                <p className="text-xs text-muted-foreground mt-1 line-clamp-3">{t.description}</p>
              )}
              <div className="flex flex-wrap gap-1 mt-2">
                {t.sub_tropes.length > 0 && (
                  <span className="text-xs bg-blue-500/10 text-blue-400 px-1.5 py-0.5 rounded">
                    {t.sub_tropes.length} sub-tropes
                  </span>
                )}
                {t.super_tropes.length > 0 && (
                  <span className="text-xs bg-purple-500/10 text-purple-400 px-1.5 py-0.5 rounded">
                    {t.super_tropes.length} super-tropes
                  </span>
                )}
                {t.examples.length > 0 && (
                  <span className="text-xs bg-green-500/10 text-green-400 px-1.5 py-0.5 rounded">
                    {t.examples.length} examples
                  </span>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
