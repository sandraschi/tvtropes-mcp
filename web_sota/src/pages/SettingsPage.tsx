import { useCallback, useEffect, useState } from "react";
import { Globe, HardDrive, Brain, Gauge, Save, Loader2 } from "lucide-react";
import { apiGet, apiPost } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { PageHero } from "@/components/layout/PageHero";

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
};

export function SettingsPage() {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [edits, setEdits] = useState<Record<string, string>>({});

  const fetchSettings = useCallback(async () => {
    setLoading(true);
    try {
      const s = await apiGet<Settings>("/api/settings");
      setSettings(s);
      setEdits({
        ollama_host: s.ollama_host,
        ollama_model: s.ollama_model,
        ollama_timeout: String(s.ollama_timeout),
        scraper_delay_min: String(s.scraper_delay_min),
        scraper_delay_max: String(s.scraper_delay_max),
        scraper_daily_budget: String(s.scraper_daily_budget),
      });
    } catch { /* ignore */ }
    setLoading(false);
  }, []);

  useEffect(() => { fetchSettings(); }, [fetchSettings]);

  const save = async () => {
    setSaving(true);
    setMsg(null);
    try {
      await apiPost("/api/settings", {
        ollama_host: edits.ollama_host,
        ollama_model: edits.ollama_model,
        ollama_timeout: parseFloat(edits.ollama_timeout) || 120,
        scraper_delay_min: parseFloat(edits.scraper_delay_min) || 8,
        scraper_delay_max: parseFloat(edits.scraper_delay_max) || 15,
        scraper_daily_budget: parseInt(edits.scraper_daily_budget) || 7000,
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
          {saving ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <Save className="h-4 w-4 mr-1" />}
          Save
        </Button>
        {msg && <span className="text-sm text-primary ml-2">{msg}</span>}
      </PageHero>

      {loading && <p className="text-sm text-muted-foreground">Loading...</p>}

      {settings && (
        <>
          {/* Read-only: server + data dir */}
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
                <p className="text-sm text-muted-foreground mt-2 break-all font-mono">{settings.data_dir}</p>
                <p className="text-xs text-muted-foreground mt-1">Set via <code className="text-primary">TVTROPES_MCP_DATA_DIR</code> env var.</p>
              </div>
            </div>
          </Card>

          {/* Editable: Ollama */}
          <Card>
            <div className="flex gap-3">
              <Brain className="h-5 w-5 text-primary shrink-0 mt-0.5" />
              <div className="min-w-0 flex-1 space-y-3">
                <CardTitle>Ollama / LM Studio</CardTitle>
                <div>
                  <label className="text-xs text-muted-foreground">Host URL</label>
                  <Input value={edits.ollama_host ?? ""} onChange={(e) => set("ollama_host", e.target.value)} className="mt-1" />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground">Model</label>
                  <Input value={edits.ollama_model ?? ""} onChange={(e) => set("ollama_model", e.target.value)} className="mt-1" />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground">Timeout (seconds)</label>
                  <Input value={edits.ollama_timeout ?? ""} onChange={(e) => set("ollama_timeout", e.target.value)} className="mt-1" type="number" />
                </div>
              </div>
            </div>
          </Card>

          {/* Editable: Scraper */}
          <Card>
            <div className="flex gap-3">
              <Gauge className="h-5 w-5 text-primary shrink-0 mt-0.5" />
              <div className="min-w-0 flex-1 space-y-3">
                <CardTitle>Scraper politeness</CardTitle>
                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <label className="text-xs text-muted-foreground">Min delay (s)</label>
                    <Input value={edits.scraper_delay_min ?? ""} onChange={(e) => set("scraper_delay_min", e.target.value)} className="mt-1" type="number" />
                  </div>
                  <div>
                    <label className="text-xs text-muted-foreground">Max delay (s)</label>
                    <Input value={edits.scraper_delay_max ?? ""} onChange={(e) => set("scraper_delay_max", e.target.value)} className="mt-1" type="number" />
                  </div>
                  <div>
                    <label className="text-xs text-muted-foreground">Daily budget</label>
                    <Input value={edits.scraper_daily_budget ?? ""} onChange={(e) => set("scraper_daily_budget", e.target.value)} className="mt-1" type="number" />
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
