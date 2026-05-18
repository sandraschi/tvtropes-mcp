import { Card, CardTitle } from "@/components/ui/card";
import { PageHero } from "@/components/layout/PageHero";

export function HelpPage() {
  return (
    <div className="space-y-6 max-w-3xl">
      <PageHero
        eyebrow="Reference"
        title="Help"
        lead="How tvtropes-mcp works, what the mirrors and caches are, and how to use the MCP tools."
      />

      <Card>
        <CardTitle>Architecture</CardTitle>
        <ul className="mt-3 text-sm text-muted-foreground space-y-2 list-disc pl-5">
          <li>Two decoupled processes share a single SQLite database in WAL mode.</li>
          <li>The <strong className="text-foreground">scraper</strong> runs as a background daemon, fetching pages at 8–15 second intervals.</li>
          <li>The <strong className="text-foreground">MCP server</strong> is read-only and can be stopped/started freely.</li>
          <li>Raw HTML is gzip-cached locally; Ollama extraction runs against the cache.</li>
        </ul>
      </Card>

      <Card>
        <CardTitle>Ports and layout</CardTitle>
        <ul className="mt-3 text-sm text-muted-foreground space-y-2 list-disc pl-5">
          <li>Backend API + MCP HTTP: port <strong className="text-foreground">10964</strong></li>
          <li>React dashboard: port <strong className="text-foreground">10965</strong></li>
          <li>Sidebar navigation, header strip, log panel at the bottom.</li>
        </ul>
      </Card>

      <Card>
        <CardTitle>MCP Tools (11)</CardTitle>
        <div className="mt-3 space-y-2 text-sm text-muted-foreground">
          <p>All tools are registered via <code className="text-primary">@mcp.tool</code> and query the local SQLite mirror:</p>
          <ul className="list-disc pl-5 space-y-1">
            <li><strong className="text-foreground">trope_search</strong> — FTS5 search over trope names and descriptions</li>
            <li><strong className="text-foreground">trope_get</strong> — full trope with examples, sub/super/sister/related</li>
            <li><strong className="text-foreground">work_tropes</strong> — all tropes for a given work</li>
            <li><strong className="text-foreground">trope_examples</strong> — examples filtered by namespace</li>
            <li><strong className="text-foreground">related_tropes</strong> — graph traversal (4 relationship types)</li>
            <li><strong className="text-foreground">namespace_list</strong> — namespaces with page counts</li>
            <li><strong className="text-foreground">random_trope</strong> — weighted random pick</li>
            <li><strong className="text-foreground">scraper_status</strong> — crawl progress, DB size, Ollama backlog</li>
            <li><strong className="text-foreground">trope_lookup_by_title</strong> — book → Literature/ cross-ref</li>
            <li><strong className="text-foreground">calibre_search</strong> — search local Calibre library</li>
            <li><strong className="text-foreground">calibre_status</strong> — check Calibre availability</li>
          </ul>
        </div>
      </Card>

      <Card>
        <CardTitle>CLI Reference</CardTitle>
        <div className="mt-3 space-y-2 text-sm text-muted-foreground">
          <p><code className="text-primary">uv run python -m tvtropes_mcp --serve</code> — API + MCP on :10964</p>
          <p><code className="text-primary">uv run python -m tvtropes_mcp --stdio</code> — MCP over stdio</p>
          <p><code className="text-primary">uv run python -m tvtropes_mcp --scrape</code> — standalone crawler daemon</p>
        </div>
      </Card>

      <Card>
        <CardTitle>Starting a crawl</CardTitle>
        <div className="mt-3 space-y-2 text-sm text-muted-foreground">
          <p>From the <strong className="text-foreground">Dashboard</strong>, enter a TVTropes URL or page path (e.g. <code className="text-primary">Anime/Planetarian</code>) and choose a depth:</p>
          <ul className="list-disc pl-5 space-y-1">
            <li><strong className="text-foreground">Depth 1:</strong> fetch the page and queue its direct links</li>
            <li><strong className="text-foreground">Depth 2:</strong> fetch the page, then fetch each linked page</li>
            <li><strong className="text-foreground">Depth 3:</strong> three hops of link-following</li>
          </ul>
          <p className="mt-2">You can also start the full background scraper with <strong className="text-foreground">Start Scraper</strong>, which will bootstrap from the sitemap and crawl all namespaces at the polite 8–15s rate over several weeks.</p>
        </div>
      </Card>

      <Card>
        <CardTitle>Ollama / LM Studio</CardTitle>
        <p className="text-sm text-muted-foreground mt-2 leading-relaxed">
          The extraction pass requires a running Ollama or LM Studio instance. By default it looks for
          Ollama at <code className="text-primary">http://localhost:11434</code>. Set{" "}
          <code className="text-primary">TVTROPES_MCP_OLLAMA_HOST</code> to point at LM Studio
          (<code className="text-primary">http://127.0.0.1:1234</code>).
        </p>
      </Card>

      <Card>
        <CardTitle>Ethics and legal</CardTitle>
        <p className="text-sm text-muted-foreground mt-2 leading-relaxed">
          All TVTropes content is CC BY-SA 3.0. The scraper runs at a human pace (8–15s per page),
          respects Cloudflare blocks with exponential backoff, and never accesses authenticated
          content. See <a className="text-primary hover:underline" href="https://github.com/sandraschi/tvtropes-mcp/blob/master/docs/ETHICS_AND_LEGAL.md" target="_blank" rel="noreferrer">docs/ETHICS_AND_LEGAL.md</a> for the full discussion.
        </p>
      </Card>

      <Card>
        <CardTitle>Source code</CardTitle>
        <a
          className="text-primary text-sm hover:underline"
          href="https://github.com/sandraschi/tvtropes-mcp"
          target="_blank"
          rel="noreferrer"
        >
          github.com/sandraschi/tvtropes-mcp
        </a>
      </Card>
    </div>
  );
}
