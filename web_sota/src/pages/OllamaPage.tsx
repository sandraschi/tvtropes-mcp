import { useCallback, useEffect, useState } from "react";
import { Brain, RefreshCw, CheckCircle, XCircle, Loader2, Save } from "lucide-react";
import { apiGet, apiPost } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { PageHero } from "@/components/layout/PageHero";

type Settings = {
  ollama_host: string;
  ollama_model: string;
  ollama_timeout: number;
};

type StatusResult = {
  running: boolean;
  host: string;
  model_configured: string;
  model_found: boolean;
  models_available: string[];
  error?: string;
};

type TestResult = {
  success: boolean;
  host: string;
  reachable: boolean;
  model_found: boolean;
  models: string[];
  error?: string;
};

export function OllamaPage() {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [status, setStatus] = useState<StatusResult | null>(null);
  const [testResult, setTestResult] = useState<TestResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [testing, setTesting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [editHost, setEditHost] = useState("");
  const [editModel, setEditModel] = useState("");
  const [saveMsg, setSaveMsg] = useState<string | null>(null);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const [s, st] = await Promise.all([
        apiGet<Settings>("/api/settings"),
        apiGet<StatusResult>("/api/ollama/status").catch(() => null),
      ]);
      setSettings(s);
      setEditHost(s.ollama_host);
      setEditModel(s.ollama_model);
      setStatus(st);
    } catch { /* ignore */ }
    setLoading(false);
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const testConnection = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const r = await apiPost<TestResult>("/api/ollama/test", { host: editHost, model: editModel });
      setTestResult(r);
    } catch (e) {
      setTestResult({ success: false, host: editHost, reachable: false, model_found: false, models: [], error: String(e) });
    }
    setTesting(false);
  };

  const saveSettings = async () => {
    setSaving(true);
    setSaveMsg(null);
    try {
      await apiPost("/api/settings", { ollama_host: editHost, ollama_model: editModel });
      setSaveMsg("Saved. Re-checking connection...");
      const st = await apiGet<StatusResult>("/api/ollama/status").catch(() => null);
      setStatus(st);
      setSaveMsg(st?.running ? "Connected and saved." : "Saved, but host not reachable.");
    } catch (e) {
      setSaveMsg("Failed to save.");
    }
    setSaving(false);
    setTimeout(() => setSaveMsg(null), 4000);
  };

  return (
    <div className="space-y-6 max-w-2xl">
      <PageHero
        eyebrow="Extraction Backend"
        title="Ollama / LM Studio"
        lead="Configure the local LLM endpoint used for structured trope extraction from cached HTML."
      />

      {loading && <div className="flex items-center gap-2 text-sm text-muted-foreground"><Loader2 className="h-4 w-4 animate-spin" /> Loading...</div>}

      {/* Connection status */}
      <Card>
        <div className="flex items-center gap-3">
          {status?.running ? <CheckCircle className="h-6 w-6 text-green-400 shrink-0" /> : <XCircle className="h-6 w-6 text-red-400 shrink-0" />}
          <div className="min-w-0">
            <CardTitle>{status?.running ? "Connected" : "Not reachable"}</CardTitle>
            <p className="text-sm text-muted-foreground truncate">{status?.host ?? editHost}</p>
          </div>
          <Button size="sm" variant="ghost" className="ml-auto shrink-0" onClick={fetchAll} disabled={loading}>
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          </Button>
        </div>
      </Card>

      {/* Configuration */}
      <Card>
        <CardTitle>Endpoint</CardTitle>
        <div className="space-y-3 mt-3">
          <div>
            <label className="text-xs text-muted-foreground block mb-1">Host URL</label>
            <Input
              value={editHost}
              onChange={(e) => setEditHost(e.target.value)}
              placeholder="http://localhost:11434"
            />
            <p className="text-[10px] text-muted-foreground mt-1">
              Use <code className="text-primary">http://127.0.0.1:1234</code> for LM Studio.
            </p>
          </div>
          <div>
            <label className="text-xs text-muted-foreground block mb-1">Model name</label>
            <Input
              value={editModel}
              onChange={(e) => setEditModel(e.target.value)}
              placeholder="qwen2.5:27b"
            />
            <p className="text-[10px] text-muted-foreground mt-1">
              Used for both extraction (Qwen 2.5 recommended) and semantic embeddings (nomic-embed-text).
            </p>
          </div>
        </div>
      </Card>

      {/* Available models */}
      {status?.models_available && status.models_available.length > 0 && (
        <Card>
          <CardTitle>Available models</CardTitle>
          <div className="flex flex-wrap gap-1.5 mt-2">
            {status.models_available.map((m) => (
              <button
                key={m}
                onClick={() => setEditModel(m)}
                className={`text-xs px-2 py-1 rounded-full border transition-colors ${
                  m.startsWith(status.model_configured)
                    ? "bg-primary/20 border-primary/40 text-primary"
                    : "bg-muted/40 border-border text-muted-foreground hover:border-primary/40"
                }`}
              >
                <Brain className="h-3 w-3 inline mr-1" />
                {m}
              </button>
            ))}
          </div>
        </Card>
      )}

      {/* Test result */}
      {testResult && (
        <div className={`rounded-lg border px-4 py-3 text-sm ${
          testResult.reachable
            ? "border-green-500/40 bg-green-500/10"
            : "border-amber-500/40 bg-amber-500/10"
        }`}>
          <p><strong>{testResult.reachable ? "Reachable" : "Not reachable"}</strong> — {testResult.host}</p>
          {testResult.reachable && (
            <p className="text-xs text-muted-foreground mt-1">
              {testResult.models.length} model(s) available
              {testResult.model_found ? "" : `, "${editModel}" not found`}
            </p>
          )}
          {testResult.error && <p className="text-xs text-amber-400 mt-1">{testResult.error}</p>}
        </div>
      )}

      {saveMsg && (
        <div className="text-sm text-primary">{saveMsg}</div>
      )}

      {/* Actions */}
      <div className="flex gap-2">
        <Button onClick={testConnection} disabled={testing || !editHost}>
          {testing ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <Brain className="h-4 w-4 mr-1" />}
          Test Connection
        </Button>
        <Button variant="default" onClick={saveSettings} disabled={saving}>
          {saving ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <Save className="h-4 w-4 mr-1" />}
          Save
        </Button>
      </div>

      <Card>
        <CardTitle>How this works</CardTitle>
        <ul className="text-sm text-muted-foreground mt-2 space-y-1 list-disc pl-5">
          <li>Extraction prompt calls Ollama to convert cached HTML into structured tropes/examples.</li>
          <li>Embeddings (semantic search) use <code className="text-primary">nomic-embed-text</code>.</li>
          <li>Settings are saved to <code className="text-primary">data/settings.json</code> and persist across restarts.</li>
          <li>Env vars (<code className="text-primary">TVTROPES_MCP_OLLAMA_*</code>) serve as defaults if settings.json is missing.</li>
        </ul>
      </Card>
    </div>
  );
}
