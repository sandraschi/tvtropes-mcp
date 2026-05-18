import { useEffect, useState } from "react";
import { Globe, HardDrive, Brain } from "lucide-react";
import { apiGet } from "@/api/client";
import { Card, CardTitle } from "@/components/ui/card";
import { PageHero } from "@/components/layout/PageHero";
import { useLogger } from "@/context/LoggerContext";

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
  const { log } = useLogger();
  const [settings, setSettings] = useState<Settings | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const s = await apiGet<Settings>("/api/settings");
        setSettings(s);
        log("info", "Settings loaded");
      } catch (e) {
        log("error", String(e));
      }
    })();
  }, [log]);

  return (
    <div className="space-y-6 max-w-2xl">
      <PageHero
        eyebrow="Configuration"
        title="Settings"
        lead="Environment-based configuration. All values are read from TVTROPES_MCP_* env vars or the .env file."
      />

      <Card>
        <div className="flex gap-3">
          <Globe className="h-5 w-5 text-primary shrink-0 mt-0.5" />
          <div>
            <CardTitle>Server</CardTitle>
            <div className="text-sm text-muted-foreground mt-1 space-y-1">
              <p>
                Host: <code className="text-primary">{settings?.host ?? "…"}</code>
              </p>
              <p>
                Port: <code className="text-primary">{settings?.port ?? "…"}</code>
              </p>
            </div>
          </div>
        </div>
      </Card>

      <Card>
        <div className="flex gap-3">
          <HardDrive className="h-5 w-5 text-primary shrink-0 mt-0.5" />
          <div>
            <CardTitle>Data directory</CardTitle>
            <p className="text-sm text-muted-foreground mt-2 break-all font-mono">{settings?.data_dir ?? "…"}</p>
            <p className="text-xs text-muted-foreground mt-2">
              Override with <code className="text-primary">TVTROPES_MCP_DATA_DIR</code> env var.
              SQLite DB + scrape cache live here.
            </p>
          </div>
        </div>
      </Card>

      <Card>
        <div className="flex gap-3">
          <Brain className="h-5 w-5 text-primary shrink-0 mt-0.5" />
          <div>
            <CardTitle>Ollama / LM Studio</CardTitle>
            <div className="text-sm text-muted-foreground mt-1 space-y-1">
              <p>
                Host: <code className="text-primary">{settings?.ollama_host ?? "…"}</code>
              </p>
              <p>
                Model: <code className="text-primary">{settings?.ollama_model ?? "…"}</code>
              </p>
              <p>
                Timeout: <code className="text-primary">{settings?.ollama_timeout ?? "…"}s</code>
              </p>
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              Set <code className="text-primary">TVTROPES_MCP_OLLAMA_HOST</code> to point at
              LM Studio (<code>http://127.0.0.1:1234</code>) or any OpenAI-compatible endpoint.
            </p>
          </div>
        </div>
      </Card>

      <Card>
        <CardTitle>Scraper politeness</CardTitle>
        <div className="text-sm text-muted-foreground mt-2 space-y-1">
          <p>
            Delay range: <code className="text-primary">{settings?.scraper_delay_min ?? "…"}–{settings?.scraper_delay_max ?? "…"}s</code>
          </p>
          <p>
            Daily budget: <code className="text-primary">{settings?.scraper_daily_budget ?? "…"}</code> pages/day
          </p>
        </div>
      </Card>
    </div>
  );
}
