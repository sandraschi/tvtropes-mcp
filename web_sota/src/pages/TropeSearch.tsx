import { useCallback, useEffect, useState } from "react";
import { Search, Loader2, BookOpen, Layers } from "lucide-react";
import { useSearchParams } from "react-router-dom";
import { apiMcpTool } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

type SearchResult = {
  id: string;
  name: string;
  snippet: string;
  score: number;
  namespace: string;
};

type SearchResponse = {
  success: boolean;
  query: string;
  results: SearchResult[];
  total: number;
};

type TropeDetail = {
  id: string;
  name: string;
  description: string | null;
  laconic: string | null;
  examples: { work: string | null; namespace: string; work_name: string; text: string }[];
  sub_tropes: { namespace: string; page_name: string }[];
  super_tropes: { namespace: string; page_name: string }[];
  sister_tropes: { namespace: string; page_name: string }[];
};

type TropeGetResponse = {
  success: boolean;
  trope: TropeDetail | null;
};

export function TropeSearch() {
  const [searchParams] = useSearchParams();
  const initialTrope = searchParams.get("trope") ?? "";

  const [query, setQuery] = useState(initialTrope);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<TropeDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const doSearch = useCallback(async () => {
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    setSelected(null);
    try {
      const r = await apiMcpTool<SearchResponse>("trope_search", { query, limit: 20 });
      if (r.success) {
        setResults(r.results);
        setTotal(r.total);
      } else {
        setError("Search returned no results");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Search failed");
    } finally {
      setLoading(false);
    }
  }, [query]);

  const openTrope = useCallback(async (id: string) => {
    setDetailLoading(true);
    try {
      const r = await apiMcpTool<TropeGetResponse>("trope_get", { trope_id: id });
      if (r.success && r.trope) {
        setSelected(r.trope);
      }
    } catch {
      // fallback
    } finally {
      setDetailLoading(false);
    }
  }, []);

  // Auto-load trope from ?trope= URL param (cross-app deep-linking)
  useEffect(() => {
    if (initialTrope && initialTrope.includes("/")) {
      openTrope(initialTrope);
    } else if (initialTrope) {
      doSearch();
    }
    // Only run on mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") doSearch();
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Trope Search</h1>
        <p className="text-muted-foreground mt-1">
          Full-text search over tropes using SQLite FTS5.
        </p>
      </div>

      <div className="flex gap-2">
        <Input
          placeholder="Search tropes... e.g. villain redemption, time loop"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          className="flex-1"
        />
        <Button onClick={doSearch} disabled={loading || !query.trim()}>
          {loading ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <Search className="h-4 w-4 mr-1" />}
          Search
        </Button>
      </div>

      {error && (
        <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-2 text-sm">
          {error}
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="space-y-3">
          {total > 0 && (
            <p className="text-sm text-muted-foreground">{total} results for "{query}"</p>
          )}
          {results.map((r) => (
            <button
              key={r.id}
              onClick={() => openTrope(r.id)}
              className="w-full text-left"
            >
              <Card className="hover:border-primary/40 transition-colors cursor-pointer">
                <div className="flex items-start gap-2">
                  <BookOpen className="h-5 w-5 text-primary shrink-0 mt-0.5" />
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <CardTitle className="text-sm">{r.name}</CardTitle>
                      <span className="text-[10px] text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
                        {r.namespace}
                      </span>
                    </div>
                    {r.snippet && (
                      <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{r.snippet}</p>
                    )}
                    <p className="text-[10px] text-muted-foreground mt-1">
                      Score: {r.score.toFixed(4)} · {r.id}
                    </p>
                  </div>
                </div>
              </Card>
            </button>
          ))}
          {loading && <p className="text-sm text-muted-foreground text-center py-4">Searching...</p>}
          {!loading && total === 0 && query && !error && (
            <p className="text-sm text-muted-foreground text-center py-4">No results. Try a different query.</p>
          )}
        </div>

        {selected && (
          <div className="space-y-4">
            <Card>
              <CardTitle>{selected.name}</CardTitle>
              {selected.laconic && (
                <p className="text-sm text-muted-foreground italic mt-2">"{selected.laconic}"</p>
              )}
              {selected.description && (
                <p className="text-sm mt-2">{selected.description}</p>
              )}
              <p className="text-[10px] text-muted-foreground mt-2">{selected.id}</p>
            </Card>

            {selected.sub_tropes.length > 0 && (
              <Card>
                <CardTitle className="text-sm">Sub-Tropes</CardTitle>
                <div className="flex flex-wrap gap-1.5 mt-2">
                  {selected.sub_tropes.map((t) => (
                    <button
                      key={`${t.namespace}/${t.page_name}`}
                      onClick={() => openTrope(`${t.namespace}/${t.page_name}`)}
                      className="text-xs bg-muted/50 px-2 py-1 rounded hover:bg-primary/20 transition-colors"
                    >
                      {t.page_name}
                    </button>
                  ))}
                </div>
              </Card>
            )}

            {selected.super_tropes.length > 0 && (
              <Card>
                <CardTitle className="text-sm">Super-Tropes</CardTitle>
                <div className="flex flex-wrap gap-1.5 mt-2">
                  {selected.super_tropes.map((t) => (
                    <button
                      key={`${t.namespace}/${t.page_name}`}
                      onClick={() => openTrope(`${t.namespace}/${t.page_name}`)}
                      className="text-xs bg-muted/50 px-2 py-1 rounded hover:bg-primary/20 transition-colors"
                    >
                      {t.page_name}
                    </button>
                  ))}
                </div>
              </Card>
            )}

            {selected.examples.length > 0 && (
              <Card>
                <CardTitle className="text-sm">Examples ({selected.examples.length})</CardTitle>
                <div className="space-y-2 mt-2 max-h-80 overflow-y-auto">
                  {selected.examples.map((ex, i) => (
                    <div key={i} className="text-xs border-b border-border/40 pb-2 last:border-0">
                      <span className="text-primary">{ex.work_name ?? ex.namespace}</span>
                      {ex.text && <p className="text-muted-foreground mt-0.5">{ex.text}</p>}
                    </div>
                  ))}
                </div>
              </Card>
            )}
          </div>
        )}

        {detailLoading && (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-6 w-6 animate-spin text-primary" />
          </div>
        )}
      </div>
    </div>
  );
}
