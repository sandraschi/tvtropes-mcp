import { useCallback, useState } from "react";
import { Layers, Loader2, Search } from "lucide-react";
import { apiGet, apiMcpTool } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

type RelationGroup = {
  sub_tropes: { namespace: string; page_name: string }[];
  super_tropes: { namespace: string; page_name: string }[];
  sister_tropes: { namespace: string; page_name: string }[];
  related_tropes: { namespace: string; page_name: string }[];
};

type RelResp = { success: boolean; trope: string } & RelationGroup;

type Trope = { namespace: string; page_name: string };

const REL_COLORS: Record<string, string> = {
  sub_tropes: "border-l-blue-500 bg-blue-500/5",
  super_tropes: "border-l-amber-500 bg-amber-500/5",
  sister_tropes: "border-l-green-500 bg-green-500/5",
  related_tropes: "border-l-purple-500 bg-purple-500/5",
};

const REL_LABELS: Record<string, string> = {
  sub_tropes: "Sub-Trope",
  super_tropes: "Super-Trope",
  sister_tropes: "Sister Trope",
  related_tropes: "Related",
};

export function TropeGraph() {
  const [tropeId, setTropeId] = useState("");
  const [graph, setGraph] = useState<RelationGroup | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<string[]>([]);

  const loadTrope = useCallback(async (id: string) => {
    setLoading(true);
    setError(null);
    try {
      const r = await apiMcpTool<RelResp>("related_tropes", { trope_id: id });
      if (r.success) {
        setGraph(r);
        setHistory((h) => [id, ...h.filter((x) => x !== id)].slice(0, 20));
      } else {
        setError("Not found in database");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, []);

  const navigate = useCallback((t: Trope) => {
    const id = `${t.namespace}/${t.page_name}`;
    setTropeId(id);
    loadTrope(id);
  }, [loadTrope]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && tropeId.trim()) loadTrope(tropeId.trim());
  };

  const allRelations = graph
    ? (Object.keys(REL_COLORS) as (keyof RelationGroup)[])
        .filter((key) => graph[key].length > 0)
    : [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Trope Graph</h1>
        <p className="text-muted-foreground mt-1">
          Traverse SubTrope, SuperTrope, SisterTrope, and Related relationships.
        </p>
      </div>

      <div className="flex gap-2">
        <Input
          placeholder="Enter trope ID... e.g. Main/AntiHero"
          value={tropeId}
          onChange={(e) => setTropeId(e.target.value)}
          onKeyDown={handleKeyDown}
          className="flex-1"
        />
        <Button onClick={() => loadTrope(tropeId.trim())} disabled={loading || !tropeId.trim()}>
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
        </Button>
      </div>

      {history.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {history.map((h) => (
            <button
              key={h}
              onClick={() => { setTropeId(h); loadTrope(h); }}
              className="text-xs bg-muted/40 px-2 py-1 rounded hover:bg-primary/20"
            >
              {h}
            </button>
          ))}
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-2 text-sm">{error}</div>
      )}

      {graph && (
        <div className="space-y-6">
          <Card>
            <div className="flex items-center gap-2">
              <Layers className="h-5 w-5 text-primary" />
              <span className="font-semibold">{graph.trope}</span>
            </div>
          </Card>

          <div className="grid gap-4 sm:grid-cols-2">
            {allRelations.map((key) => (
              <div key={key} className={`border-l-4 rounded-lg p-3 ${REL_COLORS[key]}`}>
                <h3 className="text-sm font-medium mb-2">{REL_LABELS[key]} ({graph[key].length})</h3>
                <div className="flex flex-wrap gap-1.5">
                  {graph[key].map((t: Trope) => (
                    <button
                      key={`${t.namespace}/${t.page_name}`}
                      onClick={() => navigate(t)}
                      className="text-xs bg-background/60 px-2 py-1 rounded hover:bg-primary/20 transition-colors border border-border/40"
                      title={`${t.namespace}/${t.page_name}`}
                    >
                      {t.page_name}
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>

          {allRelations.length === 0 && (
            <p className="text-sm text-muted-foreground text-center py-4">
              No relationships found for this trope.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
