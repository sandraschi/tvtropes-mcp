import { useCallback, useEffect, useState } from "react";
import { BookOpen, Globe, Layers, Loader2 } from "lucide-react";
import { apiGet, apiMcpTool } from "@/api/client";
import { Card, CardTitle } from "@/components/ui/card";

type NamespaceInfo = { namespace: string; page_count: number };
type WorkTrope = { trope_ns: string; trope_name: string; title: string | null };

type NamespaceResp = { success: boolean; namespaces: NamespaceInfo[] };
type WorkTropesResp = {
  success: boolean;
  work: { id: string };
  tropes: WorkTrope[];
  count: number;
};

const WORK_NAMESPACES = [
  "Film", "Series", "Anime", "Literature", "VideoGame",
  "WesternAnimation", "Music", "ComicBook", "Webcomic",
  "WebOriginal", "Theatre", "VisualNovel", "Manga",
];

export function WorkBrowser() {
  const [namespaces, setNamespaces] = useState<NamespaceInfo[]>([]);
  const [selectedNs, setSelectedNs] = useState<string | null>(null);
  const [works, setWorks] = useState<WorkTrope[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const r = await apiMcpTool<NamespaceResp>("namespace_list");
        if (r.success) setNamespaces(r.namespaces);
      } catch { /* ignore */ }
      setLoading(false);
    })();
  }, []);

  const browseWork = useCallback(async (namespace: string, pageName: string) => {
    const id = `${namespace}/${pageName}`;
    try {
      const r = await apiMcpTool<WorkTropesResp>("work_tropes", { work_id: id });
      if (r.success) setWorks(r.tropes);
    } catch { /* ignore */ }
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Work Browser</h1>
        <p className="text-muted-foreground mt-1">
          Browse works by namespace and see their associated tropes.
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        {WORK_NAMESPACES.map((ns) => (
          <button
            key={ns}
            onClick={() => setSelectedNs(ns === selectedNs ? null : ns)}
            className={`text-xs px-3 py-1.5 rounded-full border transition-colors ${
              selectedNs === ns
                ? "bg-primary text-primary-foreground border-primary"
                : "border-border hover:border-primary/40"
            }`}
          >
            <Globe className="h-3 w-3 inline mr-1" />
            {ns}
          </button>
        ))}
      </div>

      {loading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-primary" />
        </div>
      )}

      {!loading && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {namespaces
            .filter((ns) => !selectedNs || ns.namespace === selectedNs)
            .map((ns) => (
              <Card key={ns.namespace}>
                <div className="flex items-center gap-2">
                  <BookOpen className="h-5 w-5 text-primary shrink-0" />
                  <div>
                    <CardTitle className="text-sm">{ns.namespace}</CardTitle>
                    <p className="text-xs text-muted-foreground">{ns.page_count} pages</p>
                  </div>
                </div>
              </Card>
            ))}
        </div>
      )}

      {works.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-lg font-semibold tracking-tight">Tropes</h2>
          {works.map((t) => (
            <Card key={`${t.trope_ns}/${t.trope_name}`}>
              <div className="flex items-center gap-2">
                <Layers className="h-4 w-4 text-primary shrink-0" />
                <div>
                  <CardTitle className="text-sm">{t.title || t.trope_name}</CardTitle>
                  <p className="text-xs text-muted-foreground">{t.trope_ns}/{t.trope_name}</p>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
