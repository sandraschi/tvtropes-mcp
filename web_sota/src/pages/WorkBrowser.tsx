import { ArrowLeft, BookOpen, Globe, Layers, Loader2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { apiMcpTool } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";

type NamespaceInfo = { namespace: string; page_count: number };
type WorkItem = { work_name: string; namespace: string };
type WorkTrope = { trope_ns: string; trope_name: string; title: string | null };

type Level = "namespaces" | "works" | "tropes";

export function WorkBrowser() {
  const [namespaces, setNamespaces] = useState<NamespaceInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [level, setLevel] = useState<Level>("namespaces");
  const [selectedNs, setSelectedNs] = useState("");
  const [works, setWorks] = useState<WorkItem[]>([]);
  const [worksLoading, setWorksLoading] = useState(false);
  const [selectedWork, setSelectedWork] = useState("");
  const [tropes, setTropes] = useState<WorkTrope[]>([]);
  const [tropesLoading, setTropesLoading] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const r = await apiMcpTool<{ success: boolean; namespaces: NamespaceInfo[] }>("namespace_list");
        if (r.success) setNamespaces(r.namespaces);
      } catch { /* ignore */ }
      setLoading(false);
    })();
  }, []);

  const openNamespace = useCallback(async (ns: string) => {
    setSelectedNs(ns);
    setLevel("works");
    setWorksLoading(true);
    try {
      const r = await apiMcpTool<{ success: boolean; works: WorkItem[] }>("works_in_namespace", { namespace: ns, limit: 100 });
      if (r.success) setWorks(r.works);
    } catch { /* ignore */ }
    setWorksLoading(false);
  }, []);

  const openWork = useCallback(async (ns: string, name: string) => {
    setSelectedWork(name);
    setLevel("tropes");
    setTropesLoading(true);
    try {
      const r = await apiMcpTool<{ success: boolean; tropes: WorkTrope[] }>("work_tropes", { work_id: `${ns}/${name}` });
      if (r.success) setTropes(r.tropes);
    } catch { /* ignore */ }
    setTropesLoading(false);
  }, []);

  const goBack = useCallback(() => {
    if (level === "works") { setLevel("namespaces"); setSelectedNs(""); }
    else if (level === "tropes") { setLevel("works"); setSelectedWork(""); }
  }, [level]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-6 w-6 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Work Browser</h1>
        <p className="text-muted-foreground mt-1">
          Browse works by namespace and see their associated tropes.
        </p>
      </div>

      {level === "namespaces" && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {namespaces.map((ns) => (
            <Card key={ns.namespace}>
              <button className="w-full text-left" onClick={() => openNamespace(ns.namespace)}>
                <div className="flex items-center gap-2">
                  <BookOpen className="h-5 w-5 text-primary shrink-0" />
                  <div>
                    <CardTitle className="text-sm">{ns.namespace}</CardTitle>
                    <p className="text-xs text-muted-foreground">{ns.page_count} pages</p>
                  </div>
                </div>
              </button>
            </Card>
          ))}
        </div>
      )}

      {level === "works" && (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" onClick={goBack}><ArrowLeft className="h-4 w-4 mr-1" /> Back</Button>
            <span className="text-sm text-muted-foreground">{selectedNs}</span>
          </div>
          {worksLoading ? (
            <div className="flex justify-center py-8"><Loader2 className="h-5 w-5 animate-spin" /></div>
          ) : works.length === 0 ? (
            <p className="text-sm text-muted-foreground py-4">No works extracted yet in this namespace.</p>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {works.map((w) => (
                <Card key={w.work_name}>
                  <button className="w-full text-left" onClick={() => openWork(w.namespace, w.work_name)}>
                    <div className="flex items-center gap-2">
                      <Globe className="h-4 w-4 text-primary shrink-0" />
                      <CardTitle className="text-sm">{w.work_name}</CardTitle>
                    </div>
                  </button>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      {level === "tropes" && (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" onClick={goBack}><ArrowLeft className="h-4 w-4 mr-1" /> Back</Button>
            <span className="text-sm text-muted-foreground">{selectedNs}/{selectedWork}</span>
          </div>
          {tropesLoading ? (
            <div className="flex justify-center py-8"><Loader2 className="h-5 w-5 animate-spin" /></div>
          ) : tropes.length === 0 ? (
            <p className="text-sm text-muted-foreground py-4">No tropes found for this work.</p>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {tropes.map((t) => (
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
      )}
    </div>
  );
}
