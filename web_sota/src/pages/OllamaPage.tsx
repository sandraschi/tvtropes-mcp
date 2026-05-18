import { useCallback, useEffect, useState } from "react";
import { Brain, RefreshCw, CheckCircle, XCircle } from "lucide-react";
import { apiPost } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { PageHero } from "@/components/layout/PageHero";

type OllamaStatus = {
  running: boolean;
  host: string;
  model_configured: string;
  model_found: boolean;
  models_available: string[];
  error?: string;
};

export function OllamaPage() {
  const [status, setStatus] = useState<OllamaStatus | null>(null);
  const [loading, setLoading] = useState(true);

  const check = useCallback(async () => {
    setLoading(true);
    try {
      const r = await apiPost<OllamaStatus>("/api/ollama/status", {});
      setStatus(r);
    } catch {
      setStatus(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    check();
  }, [check]);

  return (
    <div className="space-y-6 max-w-2xl">
      <PageHero
        eyebrow="Extraction Backend"
        title="Ollama / LM Studio"
        lead="Status of the local LLM endpoint used for structured trope extraction from cached HTML."
      >
        <Button size="sm" variant="outline" onClick={check} disabled={loading}>
          <RefreshCw className={`h-4 w-4 mr-1 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </PageHero>

      <Card>
        <div className="flex items-center gap-3">
          {status?.running ? (
            <CheckCircle className="h-8 w-8 text-green-400" />
          ) : (
            <XCircle className="h-8 w-8 text-red-400" />
          )}
          <div>
            <CardTitle>{status?.running ? "Running" : "Not reachable"}</CardTitle>
            <p className="text-sm text-muted-foreground">{status?.host ?? "—"}</p>
          </div>
        </div>
      </Card>

      {status?.running && (
        <>
          <Card>
            <CardTitle>Configured model</CardTitle>
            <p className="text-sm text-muted-foreground mt-2">
              <code className="text-primary">{status.model_configured}</code>
              {status.model_found ? " — found on server" : " — not found"}
            </p>
          </Card>

          <Card>
            <CardTitle>Available models</CardTitle>
            <div className="flex flex-wrap gap-1.5 mt-2">
              {status.models_available.map((m) => (
                <span
                  key={m}
                  className={`text-xs px-2 py-1 rounded-full border ${
                    m.startsWith(status.model_configured)
                      ? "bg-primary/20 border-primary/40 text-primary"
                      : "bg-muted/40 border-border text-muted-foreground"
                  }`}
                >
                  <Brain className="h-3 w-3 inline mr-1" />
                  {m}
                </span>
              ))}
            </div>
          </Card>

          {status.error && (
            <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-2 text-sm">
              {status.error}
            </div>
          )}
        </>
      )}

      {!status?.running && !loading && (
        <Card>
          <CardTitle>Not connected</CardTitle>
          <p className="text-sm text-muted-foreground mt-2 leading-relaxed">
            Make sure Ollama or LM Studio is running. By default the server looks for Ollama at{" "}
            <code className="text-primary">http://localhost:11434</code>.
          </p>
          <p className="text-sm text-muted-foreground mt-2 leading-relaxed">
            For LM Studio, set <code className="text-primary">TVTROPES_MCP_OLLAMA_HOST=http://127.0.0.1:1234</code>.
          </p>
          {status?.error && (
            <p className="text-sm text-amber-400 mt-2">{status.error}</p>
          )}
        </Card>
      )}
    </div>
  );
}
