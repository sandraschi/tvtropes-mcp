import { ArrowRight, Brain, Gauge, Globe, HardDrive, Loader2, Save, Shield } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiGet, apiPost } from "@/api/client";
import { PageHero } from "@/components/layout/PageHero";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

type Settings = {
  host: string;
  port: number;
  data_dir: string;
  ollama_host: string;
  ollama_model: string;
  ollama_timeout: number;
  scraper_delay_min: number;
  scraper_delay_max: number;
  scraper_daily_budget: number;
  scraping_api_enabled: boolean;
  scraping_api_provider: string;
  scraping_api_key: string;
};

type LlmStatus = {
  running: boolean;
  host: string;
  model_configured: string;
  model_found: boolean;
  error?: string;
};

export function SettingsPage() {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [edits, setEdits] = useState<Record<string, string>>({});
  const [llmStatus, setLlmStatus] = useState<LlmStatus | null>(null);
  const navigate = useNavigate();

  const fetchSettings = useCallback(async () => {
    setLoading(true);
    try {
      const [s, st] = await Promise.all([
        apiGet<Settings>("/api/settings"),
        apiGet<LlmStatus>("/api/ollama/status").catch(() => null),
      ]);
      setSettings(s);
      setLlmStatus(st);
      setEdits({
        scraper_delay_min: String(s.scraper_delay_min),
        scraper_delay_max: String(s.scraper_delay_max),
        scraper_daily_budget: String(s.scraper_daily_budget),
        scraping_api_enabled: String(s.scraping_api_enabled),
        scraping_api_provider: s.scraping_api_provider,
        scraping_api_key: s.scraping_api_key || "",
      });
    } catch {
      /* ignore */
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchSettings();
  }, [fetchSettings]);

  const save = async () => {
    setSaving(true);
    setMsg(null);
    try {
      await apiPost("/api/settings", {
        scraper_delay_min: parseFloat(edits.scraper_delay_min) || 8,
        scraper_delay_max: parseFloat(edits.scraper_delay_max) || 15,
        scraper_daily_budget: parseInt(edits.scraper_daily_budget, 10) || 7000,
        scraping_api_enabled: edits.scraping_api_enabled === "true",
        scraping_api_provider: edits.scraping_api_provider || "scrapieapi",
        scraping_api_key: edits.scraping_api_key || "",
      });
      setMsg("Settings saved.");
      fetchSettings();
    } catch {
      setMsg("Failed to save.");
    }
    setSaving(false);
    setTimeout(() => setMsg(null), 3000);
  };

  const set = (key: string, val: string) => setEdits((p) => ({ ...p, [key]: val }));

  return (
    <div className="space-y-6 max-w-2xl">
      <PageHero
        eyebrow="Configuration"
        title="Settings"
        lead="Runtime settings are persisted to data/settings.json and override environment variables."
      >
        <Button size="sm" onClick={save} disabled={saving || !settings}>
          {saving ? (
            <Loader2 className="h-4 w-4 animate-spin mr-1" />
          ) : (
            <Save className="h-4 w-4 mr-1" />
          )}
          Save
        </Button>
        {msg && <span className="text-sm text-primary ml-2">{msg}</span>}
      </PageHero>

      {loading && <p className="text-sm text-muted-foreground">Loading...</p>}

      {settings && (
        <>
          <Card>
            <div className="flex gap-3">
              <Globe className="h-5 w-5 text-primary shrink-0 mt-0.5" />
              <div className="min-w-0 flex-1">
                <CardTitle>Server</CardTitle>
                <p className="text-sm text-muted-foreground mt-1">
                  {settings.host}:{settings.port}
                </p>
              </div>
            </div>
          </Card>

          <Card>
            <div className="flex gap-3">
              <HardDrive className="h-5 w-5 text-primary shrink-0 mt-0.5" />
              <div className="min-w-0 flex-1">
                <CardTitle>Data directory</CardTitle>
                <p className="text-sm text-muted-foreground mt-2 break-all font-mono">
                  {settings.data_dir}
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  Set via <code className="text-primary">TVTROPES_MCP_DATA_DIR</code> env var.
                </p>
              </div>
            </div>
          </Card>

          <Card className="border-primary/30 bg-primary/5">
            <div className="flex gap-3">
              <Brain className="h-5 w-5 text-primary shrink-0 mt-0.5" />
              <div className="min-w-0 flex-1">
                <CardTitle>LLM Provider</CardTitle>
                <p className="text-sm text-muted-foreground mt-1">
                  {llmStatus ? (
                    <>
                      <span className={llmStatus.running ? "text-green-400" : "text-red-400"}>
                        {llmStatus.running ? "Connected" : "Not reachable"}
                      </span>
                      {" — "}{llmStatus.host}
                      {llmStatus.model_configured && (
                        <>{" — "}<code className="text-primary">{llmStatus.model_configured}</code></>
                      )}
                    </>
                  ) : (
                    "Not configured"
                  )}
                </p>
                <Button
                  variant="ghost"
                  size="sm"
                  className="mt-2 -ml-2 text-primary"
                  onClick={() => navigate("/ollama")}
                >
                  Configure LLM provider <ArrowRight className="h-3 w-3 ml-1" />
                </Button>
              </div>
            </div>
          </Card>

          <Card>
            <div className="flex gap-3">
              <Gauge className="h-5 w-5 text-primary shrink-0 mt-0.5" />
              <div className="min-w-0 flex-1 space-y-3">
                <CardTitle>Scraper politeness</CardTitle>
                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <label className="text-xs text-muted-foreground">Min delay (s)</label>
                    <Input
                      value={edits.scraper_delay_min ?? ""}
                      onChange={(e) => set("scraper_delay_min", e.target.value)}
                      className="mt-1"
                      type="number"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-muted-foreground">Max delay (s)</label>
                    <Input
                      value={edits.scraper_delay_max ?? ""}
                      onChange={(e) => set("scraper_delay_max", e.target.value)}
                      className="mt-1"
                      type="number"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-muted-foreground">Daily budget</label>
                    <Input
                      value={edits.scraper_daily_budget ?? ""}
                      onChange={(e) => set("scraper_daily_budget", e.target.value)}
                      className="mt-1"
                      type="number"
                    />
                  </div>
                </div>
              </div>
            </div>
          </Card>

          <Card className="border-primary/30">
            <div className="flex gap-3">
              <Shield className="h-5 w-5 text-primary shrink-0 mt-0.5" />
              <div className="min-w-0 flex-1 space-y-3">
                <CardTitle>Scraping API (Cloudflare bypass)</CardTitle>
                <p className="text-xs text-muted-foreground">
                  Route requests through a scraping API provider instead of direct curl_cffi
                  to bypass Cloudflare protection.
                </p>
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={edits.scraping_api_enabled === "true"}
                    onChange={(e) => set("scraping_api_enabled", String(e.target.checked))}
                    className="rounded border-zinc-600 bg-zinc-800 text-primary focus:ring-primary"
                  />
                  Enable scraping API
                </label>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs text-muted-foreground">Provider</label>
                    <select
                      value={edits.scraping_api_provider ?? "scrapieapi"}
                      onChange={(e) => set("scraping_api_provider", e.target.value)}
                      className="mt-1 w-full rounded border border-zinc-600 bg-zinc-800 px-2 py-1.5 text-sm text-zinc-100"
                    >
                      <option value="scrapieapi">ScraperAPI</option>
                      <option value="scrapingbee">ScrapingBee</option>
                      <option value="zenrows">ZenRows</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-xs text-muted-foreground">API key</label>
                    <Input
                      value={edits.scraping_api_key ?? ""}
                      onChange={(e) => set("scraping_api_key", e.target.value)}
                      className="mt-1"
                      type="password"
                      placeholder="sk-..."
                    />
                  </div>
                </div>
              </div>
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
