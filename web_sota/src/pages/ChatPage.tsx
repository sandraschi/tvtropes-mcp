import { Brain, Loader2, MessageSquare, Send, User } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { apiGet, apiMcpTool, apiPost } from "@/api/client";
import { PageHero } from "@/components/layout/PageHero";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

type Message = {
  role: "user" | "assistant";
  text: string;
};

export function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      text: "I can search the trope database, look up works, traverse relationships, and check scraper status. Try asking something like:\n\n- Search for 'time loop' tropes\n- Get details on Main/ChekhovsGun\n- What are the tropes in Series/BreakingBad?\n- Random trope\n- Scraper status",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [endpoint, setEndpoint] = useState("ollama");
  const [ollamaOk, setOllamaOk] = useState<boolean | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const r = await apiGet<{ running: boolean }>("/api/ollama/status");
        setOllamaOk(r.running);
      } catch {
        setOllamaOk(false);
      }
    })();
  }, []);

  const sendMessage = useCallback(async () => {
    if (!input.trim() || loading) return;
    const userMsg = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", text: userMsg }]);
    setLoading(true);

    try {
      if (endpoint === "ollama" && ollamaOk) {
        const r = await apiPost<{ response: string }>("/api/ollama/chat", {
          model: "qwen2.5:27b",
          messages: [
            ...messages.map((m) => ({ role: m.role, content: m.text })),
            { role: "user", content: userMsg },
          ],
        });
        setMessages((prev) => [...prev, { role: "assistant", text: r.response }]);
      } else {
        // Fallback: route through MCP tools
        const cmd = userMsg.toLowerCase();
        let result: Record<string, unknown> = {};
        if (cmd.includes("search") || cmd.includes("find")) {
          const query = userMsg.replace(/search|find|for|trope/gi, "").trim() || "hero";
          result = await apiMcpTool("trope_search", { query, limit: 5 });
        } else if (cmd.includes("random")) {
          result = await apiMcpTool("random_trope", {});
        } else if (cmd.startsWith("trope_get") || !cmd.includes(" ")) {
          const id = userMsg.includes("/")
            ? userMsg.trim()
            : `Main/${userMsg.trim().replace(/\s+/g, "")}`;
          result = await apiMcpTool("trope_get", { trope_id: id });
        } else if (cmd.includes("status") || cmd.includes("scraper")) {
          result = await apiMcpTool("scraper_status", {});
        } else if (cmd.includes("work") || cmd.includes("series") || cmd.includes("film")) {
          const parts = userMsg.split(" ");
          const ns = parts.find((p) =>
            ["film", "series", "anime", "literature"].includes(p.toLowerCase()),
          );
          const name = parts.filter((p) => p !== ns).join("");
          result = await apiMcpTool("work_tropes", { work_id: `${ns ?? "Film"}/${name}` });
        }
        const text = result.success
          ? JSON.stringify(result, null, 2).slice(0, 2000)
          : "Could not process that request.";
        setMessages((prev) => [...prev, { role: "assistant", text }]);
      }
    } catch (e) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: `Error: ${e instanceof Error ? e.message : String(e)}` },
      ]);
    } finally {
      setLoading(false);
    }
  }, [input, loading, messages, endpoint, ollamaOk]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) sendMessage();
  };

  return (
    <div className="space-y-4 max-w-3xl mx-auto">
      <PageHero
        eyebrow="AI Assistant"
        title="Chat"
        lead="Ask questions about tropes, works, and relationships. Routes through MCP tools or Ollama."
      >
        <div className="flex gap-2 pt-1">
          <button
            onClick={() => setEndpoint("mcp")}
            className={`text-xs px-3 py-1 rounded-full border transition-colors ${
              endpoint === "mcp"
                ? "bg-primary text-primary-foreground border-primary"
                : "border-border hover:border-primary/40"
            }`}
          >
            <MessageSquare className="h-3 w-3 inline mr-1" /> MCP Tools
          </button>
          <button
            onClick={() => setEndpoint("ollama")}
            className={`text-xs px-3 py-1 rounded-full border transition-colors ${
              endpoint === "ollama"
                ? "bg-primary text-primary-foreground border-primary"
                : "border-border hover:border-primary/40"
            }`}
          >
            <Brain className="h-3 w-3 inline mr-1" />
            Ollama {ollamaOk === true ? "✓" : ollamaOk === false ? "✗" : "…"}
          </button>
        </div>
      </PageHero>

      <div className="h-[50vh] overflow-y-auto space-y-3 px-1">
        {messages.map((m, i) => (
          <div
            key={i}
            className={cn("flex gap-3", m.role === "user" ? "justify-end" : "justify-start")}
          >
            <Card
              className={cn("max-w-[80%] p-3", m.role === "user" ? "bg-primary/10" : "bg-card/60")}
            >
              <div className="flex items-center gap-2 mb-1">
                {m.role === "assistant" ? (
                  <Brain className="h-3.5 w-3.5 text-primary" />
                ) : (
                  <User className="h-3.5 w-3.5 text-muted-foreground" />
                )}
                <span className="text-[10px] text-muted-foreground uppercase">{m.role}</span>
              </div>
              <pre className="text-sm whitespace-pre-wrap font-sans text-foreground/90">
                {m.text}
              </pre>
            </Card>
          </div>
        ))}
        {loading && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground pl-1">
            <Loader2 className="h-4 w-4 animate-spin" /> Thinking...
          </div>
        )}
      </div>

      <div className="flex gap-2">
        <Input
          placeholder="Ask about tropes, works, or the scraper..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          className="flex-1"
        />
        <Button onClick={sendMessage} disabled={loading || !input.trim()}>
          <Send className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
