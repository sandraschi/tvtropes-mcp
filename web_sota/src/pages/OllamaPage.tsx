import { Brain, CheckCircle, Loader2, RefreshCw, Save, XCircle } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { apiGet, apiPost } from "@/api/client";
import { PageHero } from "@/components/layout/PageHero";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";

type DiscoverProvider = {
  id: string;
  label: string;
  base_url: string;
  models: string[];
  online: boolean;
  error?: string;
};

type DiscoverResult = {
  providers: DiscoverProvider[];
  configured_host: string;
  configured_model: string;
  api_mode: string;
  configured_openai_model: string;
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
  const [discover, setDiscover] = useState<DiscoverResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [testing, setTesting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState<string | null>(null);

  const [selectedProvider, setSelectedProvider] = useState("ollama");
  const [endpointUrl, setEndpointUrl] = useState("http://localhost:11434");
  const [selectedModel, setSelectedModel] = useState("");
  const [testResult, setTestResult] = useState<TestResult | null>(null);

  const currentProviders = discover?.providers ?? [];
  const currentProvider = currentProviders.find((p) => p.id === selectedProvider);
  const providerModels = currentProvider?.models ?? [];
  const providerOnline = currentProvider?.online ?? false;

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const d = await apiGet<DiscoverResult>("/api/llm/discover");
      setDiscover(d);

      const configuredModel = d.api_mode === "openai" ? d.configured_openai_model : d.configured_model;
      setSelectedModel(configuredModel || "");

      const onlineProviders = d.providers.filter((p) => p.online && p.models.length > 0);
      if (onlineProviders.length > 0) {
        const match = onlineProviders.find((p) =>
          (d.api_mode === "ollama" && p.id === "ollama") ||
          (d.api_mode === "openai" && p.id === "lmstudio")
        );
        if (match) {
          setSelectedProvider(match.id);
          setEndpointUrl(match.base_url);
        } else {
          setSelectedProvider(onlineProviders[0].id);
          setEndpointUrl(onlineProviders[0].base_url);
        }
      } else {
        setSelectedProvider(d.api_mode === "openai" ? "lmstudio" : "ollama");
        setEndpointUrl(d.configured_host || "http://localhost:11434");
      }
    } catch {
      /* offline — defaults stay */
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  useEffect(() => {
    if (currentProvider?.base_url) {
      setEndpointUrl(currentProvider.base_url);
    }
  }, [selectedProvider, currentProvider]);

  const testConnection = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const r = await apiPost<TestResult>("/api/ollama/test", { host: endpointUrl, model: selectedModel });
      setTestResult(r);
    } catch (e) {
      setTestResult({
        success: false, host: endpointUrl, reachable: false,
        model_found: false, models: [], error: String(e),
      });
    }
    setTesting(false);
  };

  const saveSettings = async () => {
    setSaving(true);
    setSaveMsg(null);
    try {
      const apiMode = selectedProvider === "lmstudio" ? "openai" : "ollama";
      await apiPost("/api/settings", {
        ollama_host: endpointUrl,
        ollama_model: selectedModel,
        api_mode: apiMode,
        openai_chat_model: apiMode === "openai" ? selectedModel : undefined,
      });
      setSaveMsg(providerOnline ? "Connected and saved." : "Saved, but provider not reachable.");
    } catch {
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

      {loading && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" /> Detecting providers...
        </div>
      )}

      {/* Connection status */}
      <Card>
        <div className="flex items-center gap-3">
          {loading ? (
            <Loader2 className="h-6 w-6 text-muted-foreground shrink-0 animate-spin" />
          ) : providerOnline ? (
            <CheckCircle className="h-6 w-6 text-green-400 shrink-0" />
          ) : (
            <XCircle className="h-6 w-6 text-red-400 shrink-0" />
          )}
          <div className="min-w-0">
            <CardTitle>
              {loading ? "Detecting..." : providerOnline ? "Connected" : "Not reachable"}
            </CardTitle>
            <p className="text-sm text-muted-foreground truncate">
              {currentProvider?.label ?? selectedProvider} — {endpointUrl || "no endpoint"}
              {!loading && !providerOnline && currentProvider?.error && (
                <> <span className="text-amber-400">({currentProvider.error})</span></>
              )}
            </p>
          </div>
          <Button
            size="sm" variant="ghost" className="ml-auto shrink-0"
            onClick={fetchAll} disabled={loading}
          >
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          </Button>
        </div>
      </Card>

      {/* Provider & model selection */}
      <Card>
        <CardTitle>Provider</CardTitle>
        <div className="space-y-3 mt-3">
          <div>
            <label className="text-xs text-muted-foreground block mb-1">
              Local LLM provider
            </label>
            <Select
              value={selectedProvider}
              onChange={(e) => setSelectedProvider(e.target.value)}
              data-testid="provider-select"
            >
              <option value="ollama">
                Ollama {currentProviders.find((p) => p.id === "ollama")?.online ? "(online)" : "(offline)"}
              </option>
              <option value="lmstudio">
                LM Studio {currentProviders.find((p) => p.id === "lmstudio")?.online ? "(online)" : "(offline)"}
              </option>
            </Select>
          </div>
          <div>
            <label className="text-xs text-muted-foreground block mb-1">
              Endpoint URL
            </label>
            <Input
              value={endpointUrl}
              onChange={(e) => setEndpointUrl(e.target.value)}
              placeholder="http://localhost:11434"
              data-testid="endpoint-input"
            />
            <p className="text-xs text-muted-foreground mt-1">
              Auto-detected from provider. Override for custom endpoints.
            </p>
          </div>
        </div>
      </Card>

      {/* Model selection */}
      <Card>
        <CardTitle>Model</CardTitle>
        <div className="mt-3">
          {providerModels.length > 0 ? (
            <>
              <label className="text-xs text-muted-foreground block mb-1">
                Select model ({providerModels.length} available)
              </label>
              <Select
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
                data-testid="model-select"
              >
                <option value="">— Select a model —</option>
                {providerModels.map((m) => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </Select>
            </>
          ) : (
            <>
              <label className="text-xs text-muted-foreground block mb-1">
                Model name
              </label>
              <Input
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
                placeholder={selectedProvider === "lmstudio" ? "qwen/qwen3.6-27b" : "qwen2.5:27b"}
                data-testid="model-input"
              />
              <p className="text-xs text-muted-foreground mt-1">
                {providerOnline ? "Models could not be fetched." : "Provider offline — enter model name manually."}
              </p>
            </>
          )}
          <p className="text-xs text-muted-foreground mt-2">
            Used for both extraction (Qwen 2.5 recommended) and semantic embeddings
            (nomic-embed-text).
          </p>
        </div>
      </Card>

      {/* Test result */}
      {testResult && (
        <div
          className={`rounded-lg border px-4 py-3 text-sm ${
            testResult.reachable
              ? "border-green-500/40 bg-green-500/10"
              : "border-amber-500/40 bg-amber-500/10"
          }`}
          data-testid="test-result"
        >
          <p>
            <strong>{testResult.reachable ? "Reachable" : "Not reachable"}</strong> —{" "}
            {testResult.host}
          </p>
          {testResult.reachable && (
            <p className="text-xs text-muted-foreground mt-1">
              {testResult.models.length} model(s) available
              {testResult.model_found ? "" : `, "${selectedModel}" not found`}
            </p>
          )}
          {testResult.error && <p className="text-xs text-amber-400 mt-1">{testResult.error}</p>}
        </div>
      )}

      {saveMsg && <div className="text-sm text-primary" data-testid="save-msg">{saveMsg}</div>}

      {/* Actions */}
      <div className="flex gap-2">
        <Button onClick={testConnection} disabled={testing || !endpointUrl} data-testid="test-btn">
          {testing ? (
            <Loader2 className="h-4 w-4 animate-spin mr-1" />
          ) : (
            <Brain className="h-4 w-4 mr-1" />
          )}
          Test Connection
        </Button>
        <Button variant="default" onClick={saveSettings} disabled={saving} data-testid="save-btn">
          {saving ? (
            <Loader2 className="h-4 w-4 animate-spin mr-1" />
          ) : (
            <Save className="h-4 w-4 mr-1" />
          )}
          Save
        </Button>
      </div>

      <Card>
        <CardTitle>How this works</CardTitle>
        <ul className="text-sm text-muted-foreground mt-2 space-y-1 list-disc pl-5">
          <li>
            Provider and model are auto-detected on page load by probing local endpoints.
          </li>
          <li>
            Ollama uses native <code className="text-primary">/api/tags</code>; LM Studio uses{" "}
            <code className="text-primary">/v1/models</code> (OpenAI-compatible API).
          </li>
          <li>
            Extraction prompts call the selected model to convert cached HTML into structured
            tropes and examples.
          </li>
          <li>
            Embeddings (semantic search) use{" "}
            <code className="text-primary">nomic-embed-text</code>.
          </li>
          <li>
            Settings are saved to <code className="text-primary">data/settings.json</code> and
            persist across restarts.
          </li>
        </ul>
      </Card>
    </div>
  );
}
