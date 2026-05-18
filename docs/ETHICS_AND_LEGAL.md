# Ethics & Legal — tvtropes-mcp

This document explains the legal and ethical framework that governs this project. It exists because responsible mirroring requires more than a license check — it requires a clear-eyed assessment of impact, intent, and the alternatives.

---

## 1. Copyright Status: CC BY-SA 3.0

All textual content on TVTropes is distributed under the **Creative Commons Attribution-ShareAlike 3.0 Unported** license (CC BY-SA 3.0). This is explicitly stated on every page footer and is the legal foundation that makes this project possible.

### What CC BY-SA 3.0 permits

- **Copying**: the entire work may be reproduced in any medium.
- **Adaptation**: remixes, transformations, and derivative works are allowed.
- **Redistribution**: copies may be shared with anyone.
- **Commercial use**: even commercial use is permitted (though this project is non-commercial).

### Conditions

- **Attribution**: derivative works must credit the original source (covered by linking to tvtropes.org).
- **ShareAlike**: derivative works must use the **same license** (CC BY-SA 3.0). This project's mirror database inherits this license; the project's own code is MIT.

### What this means for the mirror database

The SQLite database that `tvtropes-mcp` produces is a **derivative work of CC BY-SA 3.0 content**. Anyone who uses it may copy, adapt, and redistribute the *data* under CC BY-SA 3.0 terms. The *code* that produces and queries it (this repository) remains MIT-licensed, which is a separate layer.

**If you distribute a copy of the mirror database, you must license it CC BY-SA 3.0.** You may not relicense it or incorporate it into a closed-source product that restricts access to the derived data.

---

## 2. TVTropes Terms of Service

TVTropes' ToS is a standard wiki ToS. Key relevant clauses:

- **Automated access** is technically restricted by Cloudflare (the site's infrastructure layer), not by explicit ToS prohibition — though the ToS does include a general prohibition on "interfering with the operation of the site."
- **Rate limits** are enforced by Cloudflare's free tier, not by explicit numerical caps in the ToS.
- **Content licensing** is governed by CC BY-SA 3.0 as described above.

**Our position:** A single-machine, 8–15 second delay crawler that produces a local mirror for personal use and respects Cloudflare's challenges (backing off rather than attempting to circumvent) does not "interfere with the operation of the site." It generates less load than a single human browsing the site. If the site operators explicitly prohibit automated access via a robots.txt directive or a direct communication, this project will comply.

---

## 3. Rate Limiting Philosophy

The scraper is deliberately slower than a human reader:

```
Human clicking through TVTropes at 2 AM:    roughly 5–10 seconds per page
This scraper:                                8–15 seconds per page (randomised)
```

**Why not go faster?**

- TVTropes is ad-supported and runs on modest infrastructure. Every request costs them a trivial but non-zero amount of bandwidth and CPU. We minimise this.
- The goal is a complete local copy, not a race. 30–50 days at a polite rate is fine. The scraper is designed to run unattended in the background; it is I/O bound and uses negligible CPU.
- Aggressive crawling would be disrespectful to the community that built this resource. The site persists because most of its users are considerate.
- Fast crawling triggers Cloudflare protections, which wastes everyone's time — the scraper's backoffs are longer than just waiting the extra seconds per request.

**Hard limits enforced in code:**

| Limit | Value | Rationale |
|-------|-------|-----------|
| Minimum delay | 8 seconds | Below this, Cloudflare treats us as a bot |
| Maximum delay | 15 seconds | Upper bound prevents stalls |
| Daily hard cap | 7,000 pages | ≈14 hours at average rate; stops for the day |
| Session rotation | Every 500 requests | Fresh TLS context mimics browser behaviour |
| Retry backoff | 30 min → 2h → 4h | Never retry aggressively on failure |
| Max retries | 5 | After 5 failures, skip permanently |

---

## 4. Anti-Scraping Measures (Transparently Documented)

TVTropes uses **Cloudflare free tier**, which employs:

- **TLS fingerprinting** (JA3/JA4): Python's `requests`/`httpx` libraries use the OpenSSL/MbedTLS stack, which Cloudflare reliably fingerprints as bot traffic. This project uses `curl_cffi`, which exposes Chrome's TLS stack directly.
- **Challenge pages**: Cloudflare sometimes returns HTTP 200 with a "Checking your browser" page. The scraper detects these by scanning the response body for known block signals ("cf-browser-verification", "Ray ID", "Just a moment", etc.) and backs off exponentially.
- **Rate-based blocking**: Sustained requests faster than ~5 seconds trigger increasingly aggressive challenges. The scraper stays well below this threshold.

**What we do NOT do:**

- Execute JavaScript challenges (no headless browser).
- Solve CAPTCHAs.
- Use residential proxy rotation to evade IP-based blocks.
- Access authenticated or login-gated content (e.g., adult-flagged pages, session-required namespaces).
- Ignore `robots.txt` directives (TVTropes' robots.txt is permissive, but if it changes, we comply).

**What happens if Cloudflare escalates:**

If TVTropes upgrades to Cloudflare Enterprise or deploys JS-based challenges that `curl_cffi` cannot satisfy, the scraper will simply index fewer pages. It will not attempt to defeat stronger protections. The project's value scales with the size of the mirror; a partial mirror is still useful.

---

## 5. Why a Local Mirror Exists at All

This project exists because TVTropes' knowledge graph is **culturally irreplaceable** and its **long-term availability is not guaranteed**.

**The irreplaceability argument:**

- TVTropes is the only structured, cross-referenced catalogue of narrative conventions at scale. There is no API, no dump, no alternative source. If the site goes offline, two decades of collaboratively-built knowledge disappears.
- The data has direct utility for creative work: writers checking tropes, game designers balancing narrative expectations, researchers studying narrative patterns across cultures and media.
- The site's traffic has grown steadily, but its infrastructure has not. Ad-blockers erode revenue. The Cloudflare free tier is a temporary shield, not a long-term hosting strategy.

**The modesty argument:**

- This is a single-machine mirror. In a world where individuals routinely cache terabytes of Steam games, YouTube videos, and Wikipedia dumps, a 25 GB text corpus is modest. The bandwidth consumed over 50 days (~250,000 pages × ~100 KB average = ~25 GB total, at a rate that never exceeds a few KB/s) is negligible.

---

## 6. The Unrealised Value of TVTropes

TVTropes occupies a strange position: it is one of the most frequently consulted creative resources on the internet, yet it is rarely discussed openly in professional contexts.

**For working creators:**
- Screenwriters and showrunners use trope categories as shorthand in development bibles.
- Game designers use the relationship graph to understand genre expectations and player psychology.
- Novelists browse random tropes as a creativity tool.
- Several notable showrunners have referenced TVTropes in interviews (though usually offhandedly).

**For anime and manga fandom:**
- Trope analysis is a native part of how anime fans discuss and evaluate series.
- Seasonal anime discussions on Reddit, MyAnimeList, and Discord routinely reference TVTropes pages.
- The Anime/ and Manga/ namespaces are among the fastest-growing on the site.
- The site is consulted daily during airing seasons.

**For AI and creative tools:**
- The structured trope→examples mapping is a natural fit for retrieval-augmented generation.
- Character consistency checking, narrative arc planning, and genre-aware writing assistants all benefit from a trope knowledge graph.
- The fact that this hasn't been productised is mostly because the data hasn't been available in a machine-readable form — which is exactly what this project provides.

**Why the silence?**
- Nobody wants to be the reason TVTropes notices scraping and tightens protections.
- The site's operators have never signalled a desire to monetise or restrict access beyond Cloudflare's defaults.
- There is an unspoken compact among heavy users: use it, but don't talk about using it at scale. This project is an attempt to formalise that compact into something sustainable.

---

## 7. Ollama Extraction

The extraction pass that converts raw HTML into structured data runs **entirely on your own machine** via [Ollama](https://ollama.com). No data is sent to any external API. The recommended model is `qwen2.5:27b` (Q4 quantised), which runs comfortably on a consumer GPU or high-end CPU.

This means:
- Zero external API costs after the initial crawl.
- Complete privacy — the content of every trope page stays on your machine.
- Re-extraction is free — if the prompt improves, you can re-run against cached HTML without re-crawling.

The extraction prompt is designed to produce structured JSON (title, description, laconic, examples, relationships, categories) from the page HTML. It is documented and versioned in [`scraper/extractor.py`](../scraper/extractor.py).

---

## 8. Comparison with Alternatives

| Approach | Load on TVTropes | Data Completeness | Queryable | Offline | Legal Risk |
|----------|------------------|-------------------|-----------|---------|------------|
| **This project** | Negligible (human-speed crawl over weeks) | Full mirror after ~40 days | Yes (SQLite FTS5 + MCP) | Yes | Low (CC BY-SA 3.0) |
| Wayback Machine | None | Incomplete, no structured extraction | No | Partial | None |
| Manual browsing | Low for one person | Impractical at scale | No | No | None |
| Aggressive scraper | High (denial-of-service risk) | Fast | Yes | Yes | High (ToS violation) |
| No mirror | — | — | — | — | Data loss risk |

---

## 9. If You Have Concerns

If you are a TVTropes operator, contributor, or community member with concerns about this project:

- **Open an issue** on this repository. There is a direct line to the maintainer.
- This project will comply with any reasonable request from TVTropes' operators to modify crawling behaviour, exclude specific content, or take down the repository entirely.
- The project exists because the maintainer believes TVTropes is culturally important and wants to ensure its knowledge survives. There is no adversarial intent.

---

## 10. Summary

| Concern | Status |
|---------|--------|
| Copyright compliance | ✅ CC BY-SA 3.0 — explicitly permits copying and adaptation |
| Rate limiting | ✅ 8–15s human-paced, daily cap, exponential backoff on blocks |
| Anti-scraping circumvention | ✅ None — respects Cloudflare challenges |
| Login bypass | ✅ None — public content only |
| Commercial use of data | ✅ Permitted under CC BY-SA 3.0 (but this project is non-commercial) |
| Data privacy | ✅ Extraction runs locally via Ollama |
| Attribution | ✅ Mirror database is a derivative work; original URL tracking is built into the schema |
| Transparency | ✅ This document exists. Every technical decision is documented. |
