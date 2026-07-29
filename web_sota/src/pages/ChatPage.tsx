import { Brain, Download, Eraser, Loader2, Send, Sparkles, User } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { apiGet } from "@/api/client";
import { apiMcpTool } from "@/api/client";
import { PageHero } from "@/components/layout/PageHero";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

const LS_HISTORY = "tvtropes-mcp-chat-history";
const LS_PERSONALITY = "tvtropes-mcp-chat-personality";
const MAX_HISTORY = 100;

type Message = { role: "user" | "assistant"; text: string };

const PERSONALITIES = [
  { id: "trope-expert", label: "Trope Expert", prompt: "You are a TV Tropes expert. Know every trope, every work, every relationship." },
  { id: "writer", label: "Writer", prompt: "You are a writer using tropes as tools. Help users understand how to use tropes effectively in their own writing." },
  { id: "analyst", label: "Media Analyst", prompt: "You are a media analyst. Examine patterns, trends, and cultural significance of tropes across works." },
  { id: "custom", label: "Custom", prompt: "" },
];

const EXAMPLE_PROMPTS = [
  "Search for 'time loop' tropes",
  "Get details on Main/ChekhovsGun",
  "Tropes in Series/BreakingBad",
  "Random trope",
  "Scraper status",
  "Search for works with 'hero' trope",
  "What tropes are in Film/Inception?",
  "Look up Literature/Dune",
  "Semantic search: redemption arc",
];

function loadHistory(): Message[] {
  try { const s = localStorage.getItem(LS_HISTORY); if (s) return JSON.parse(s); } catch { /* ignore */ }
  return [];
}

export function ChatPage() {
  const [messages, setMessages] = useState<Message[]>(() => {
    const saved = loadHistory();
    if (saved.length > 0) return saved;
    return [{ role: "assistant", text: "I can search the trope database, look up works, and traverse relationships. Try the prompts below or type your own question." }];
  });
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState("mcp");
  const [llmOk, setLlmOk] = useState<boolean | null>(null);
  const [personality, setPersonality] = useState(() => localStorage.getItem(LS_PERSONALITY) || "trope-expert");

  const [skillContent, setSkillContent] = useState("");
  const [skillName, setSkillName] = useState("");
  const [detectedProvider, setDetectedProvider] = useState("");
  const [detectedModel, setDetectedModel] = useState("");
  const savedProvider = (() => { try { return localStorage.getItem("llm_provider"); } catch { return null; } })();
  const savedModel = (() => { try { return localStorage.getItem("llm_model"); } catch { return null; } })();

  const chatEndRef = useRef<HTMLDivElement>(null);
  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  useEffect(() => {
    try { localStorage.setItem(LS_HISTORY, JSON.stringify(messages.slice(-MAX_HISTORY))); } catch { /* ignore */ }
  }, [messages]);

  useEffect(() => { localStorage.setItem(LS_PERSONALITY, personality); }, [personality]);

  useEffect(() => {
    (async () => {
      try {
        const s = await apiGet<{ skills: { name: string; uri: string }[] }>("/api/skills");
        if (s.skills?.length > 0) {
          const primary = s.skills[0];
          setSkillName(primary.name);
          const c = await apiGet<{ content: string }>(`/api/skills/${primary.name}`);
          if (c.content) setSkillContent(c.content);
        }
      } catch { /* no skills */ }
    })();
  }, []);

  useEffect(() => {
    (async () => {
      try {
        const d = await apiGet<{ providers: { id: string; base_url: string; online: boolean; models: string[] }[] }>("/api/llm/discover");
        const online = d.providers.find((p) => p.id === (savedProvider ?? "ollama") && p.online)
          ?? d.providers.find((p) => p.online);
        if (online) {
          setDetectedProvider(online.base_url);
          const chosen = (savedModel && online.models.includes(savedModel)) ? savedModel : (online.models[0] || "");
          setDetectedModel(chosen);
          setLlmOk(true);
        } else { setLlmOk(false); }
      } catch { setLlmOk(false); }
    })();
  }, []);

  const buildSystemPrompt = useCallback(() => {
    const person = PERSONALITIES.find((p) => p.id === personality);
    const rolePrompt = person?.prompt || "";
    if (personality === "custom") return skillContent || "You are a helpful TVTropes assistant.";
    if (skillContent) return `${skillContent}\n\n---\n\n## Role\n${rolePrompt}`;
    return rolePrompt || "You are a helpful TVTropes assistant.";
  }, [personality, skillContent]);

  const sendMessage = useCallback(async () => {
    if (!input.trim() || loading) return;
    const userMsg = input.trim();
    setInput("");
    const updated = [...messages, { role: "user" as const, text: userMsg }];
    setMessages(updated);
    setLoading(true);

    try {
      if (mode === "llm" && llmOk) {
        const systemPrompt = buildSystemPrompt();
        const chatMsgs = [{ role: "system", content: systemPrompt }];
        for (const m of updated) {
          chatMsgs.push({ role: m.role === "assistant" ? "assistant" : "user", content: m.text });
        }

        const baseUrl = detectedProvider || "http://localhost:11434";
        const model = detectedModel || "qwen2.5:27b";

        const r = await fetch(`${baseUrl}/v1/chat/completions`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ model, messages: chatMsgs, temperature: 0.7, stream: true }),
        });

        if (!r.ok || !r.body) {
          const errText = await r.text().catch(() => "stream failed");
          setMessages((prev) => [...prev, { role: "assistant", text: `LLM error: ${r.status} ${errText}` }]);
          setLoading(false);
          return;
        }

        const reader = r.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let fullText = "";

        const assistantMsg = { role: "assistant" as const, text: "" };
        setMessages((prev) => [...prev, assistantMsg]);

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";
          for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed || !trimmed.startsWith("data: ")) continue;
            const jsonStr = trimmed.slice(6);
            if (jsonStr === "[DONE]") break;
            try {
              const chunk = JSON.parse(jsonStr);
              const delta = chunk?.choices?.[0]?.delta?.content || "";
              fullText += delta;
              setMessages((prev) => {
                const next = [...prev];
                next[next.length - 1] = { role: "assistant", text: fullText };
                return next;
              });
            } catch { /* parse error, skip */ }
          }
        }
      } else if (mode === "mcp") {
        const cmd = userMsg.toLowerCase();
        let result: Record<string, unknown> = {};
        if (cmd.includes("search") || cmd.includes("find")) {
          const query = userMsg.replace(/search|find|for|trope/gi, "").trim() || "hero";
          result = await apiMcpTool("trope_search", { query, limit: 5 });
        } else if (cmd.includes("random")) {
          result = await apiMcpTool("random_trope", {});
        } else if (cmd.includes("/")) {
          result = await apiMcpTool("trope_get", { trope_id: userMsg.trim() });
        } else if (cmd.includes("status") || cmd.includes("scraper")) {
          result = await apiMcpTool("scraper_status", {});
        } else {
          result = await apiMcpTool("trope_search", { query: userMsg, limit: 5 });
        }
        const text = result.success ? JSON.stringify(result, null, 2).slice(0, 3000) : "Could not process that request.";
        setMessages((prev) => [...prev, { role: "assistant", text }]);
      } else {
        setMessages((prev) => [...prev, { role: "assistant", text: "LLM endpoint not available. Switch to MCP Tools mode or start Ollama/LM Studio." }]);
      }
    } catch (e) {
      setMessages((prev) => [...prev, { role: "assistant", text: `Error: ${e instanceof Error ? e.message : String(e)}` }]);
    } finally {
      setLoading(false);
    }
  }, [input, loading, messages, mode, llmOk, buildSystemPrompt, detectedProvider, detectedModel]);

  const handleClear = useCallback(() => {
    setMessages([]);
    try { localStorage.removeItem(LS_HISTORY); } catch { /* ignore */ }
  }, []);

  const handleExport = useCallback(() => {
    const text = messages.map((m) => `[${m.role.toUpperCase()}] ${m.text}`).join("\n\n---\n\n");
    const blob = new Blob([text], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url; a.download = `tvtropes-mcp-chat-${new Date().toISOString().slice(0, 10)}.txt`;
    a.click(); URL.revokeObjectURL(url);
  }, [messages]);

  const handleKeyDown = (e: React.KeyboardEvent) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); } };

  return (
    <div data-testid="chat-page" className="space-y-4 max-w-3xl mx-auto">
      <PageHero eyebrow="AI Assistant" title="Chat" lead="Ask about tropes, works, relationships. MCP Tools mode runs tool calls directly; LLM mode uses a local model for natural language.">
        <div data-testid="chat-controls" className="flex flex-wrap items-center gap-2 pt-1">
          <button onClick={() => setMode("mcp")} className={`text-xs px-3 py-1 rounded-full border transition-colors ${mode === "mcp" ? "bg-primary text-primary-foreground border-primary" : "border-border hover:border-primary/40"}`}>
            <Sparkles className="h-3 w-3 inline mr-1" /> MCP Tools
          </button>
          <button onClick={() => setMode("llm")} className={`text-xs px-3 py-1 rounded-full border transition-colors ${mode === "llm" ? "bg-primary text-primary-foreground border-primary" : "border-border hover:border-primary/40"}`}>
            <Brain className="h-3 w-3 inline mr-1" /> LLM {llmOk === true ? "\u2713" : llmOk === false ? "\u2717" : "\u2026"}
          </button>
          {skillName && <span className="text-xs uppercase tracking-wider text-muted-foreground font-mono bg-muted/50 px-2 py-0.5 rounded">skill:{skillName}</span>}
          <select data-testid="personality-select" value={personality} onChange={(e) => setPersonality(e.target.value)} className="bg-muted text-xs text-foreground border border-border rounded px-2 py-1">
            {PERSONALITIES.map((p) => <option key={p.id} value={p.id}>{p.label}</option>)}
          </select>
          <div className="flex gap-1">
            <Button data-testid="chat-export" size="icon" variant="ghost" onClick={handleExport} disabled={messages.length === 0} className="h-7 w-7" title="Export chat"><Download className="h-3 w-3" /></Button>
            <Button data-testid="chat-clear" size="icon" variant="ghost" onClick={handleClear} disabled={messages.length === 0} className="h-7 w-7" title="Clear chat"><Eraser className="h-3 w-3" /></Button>
          </div>
        </div>
      </PageHero>

      <div data-testid="example-prompts" className="flex flex-wrap gap-1.5">
        {EXAMPLE_PROMPTS.map((p) => (
          <button key={p} onClick={() => { setInput(p); }} className="flex items-center gap-1 px-2 py-1 rounded-full text-xs border border-border text-muted-foreground hover:text-foreground hover:border-primary/40 transition-colors">
            <Sparkles className="w-2.5 h-2.5" />{p}
          </button>
        ))}
      </div>

      <div data-testid="chat-messages" className="h-[45vh] overflow-y-auto space-y-3 px-1">
        {messages.map((m, i) => (
          <div key={i} className={cn("flex gap-3", m.role === "user" ? "justify-end" : "justify-start")}>
            <Card className={cn("max-w-[80%] p-3", m.role === "user" ? "bg-primary/10" : "bg-card/60")}>
              <div className="flex items-center gap-2 mb-1">
                {m.role === "assistant" ? <Brain className="h-3.5 w-3.5 text-primary" /> : <User className="h-3.5 w-3.5 text-muted-foreground" />}
                <span className="text-xs text-muted-foreground uppercase">{m.role}</span>
              </div>
              <pre className="text-sm whitespace-pre-wrap font-sans text-foreground/90">{m.text}</pre>
            </Card>
          </div>
        ))}
        {loading && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground pl-1">
            <Loader2 className="h-4 w-4 animate-spin" /> Thinking...
          </div>
        )}
        <div ref={chatEndRef} />
      </div>

      <div className="flex gap-2">
        <Input data-testid="chat-input" placeholder="Ask about tropes, works, or the scraper..." value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={handleKeyDown} className="flex-1" />
        <Button data-testid="chat-send" onClick={sendMessage} disabled={loading || !input.trim()}>
          <Send className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
