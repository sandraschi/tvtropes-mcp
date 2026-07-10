"""BeautifulSoup HTML parsing helpers for TVTropes pages."""

from __future__ import annotations

import logging
import re
from typing import Any
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

log = logging.getLogger(__name__)

TVTROPES_DOMAIN = "tvtropes.org"
TVTROPES_BASE = "https://tvtropes.org"

PAGE_PATTERN = re.compile(r"^/(?:pmwiki/)?pmwiki\.php/([^/]+)/(.+)$")
NAMESPACE_PATTERN = re.compile(r"^[A-Z][a-zA-Z0-9]*$")
SKIP_NAMESPACES = frozenset({"SandBox", "Administrivia", "Ptitle", "Help", "Discussion"})

BLOCK_SIGNALS = [
    "Just a moment",
    "Checking your browser",
    "cf-browser-verification",
    "Ray ID",
    "Please enable JavaScript",
    "DDoS protection by Cloudflare",
    "cf_clearance",
]


def is_cloudflare_blocked(html: str) -> bool:
    return any(signal in html for signal in BLOCK_SIGNALS)


def extract_page_title(soup: BeautifulSoup) -> str | None:
    h1 = soup.find("h1", class_="entry-title")
    if h1:
        return h1.get_text(strip=True)
    title_tag = soup.find("title")
    if title_tag:
        text = title_tag.get_text(strip=True)
        text = re.sub(r"\s*[-–—|]\s*TV Tropes.*$", "", text).strip()  # noqa: RUF001
        return text if text else None
    return None


def extract_page_description(soup: BeautifulSoup) -> str | None:
    meta = soup.find("meta", attrs={"name": "description"})
    if meta and meta.get("content"):
        return meta["content"].strip()
    folder = soup.find("div", class_="folder")
    if folder:
        p = folder.find("p")
        if p:
            return p.get_text(strip=True)[:500]
    return None


def extract_laconic(soup: BeautifulSoup) -> str | None:
    quote = soup.find("blockquote", class_="laconic")
    if quote:
        return quote.get_text(strip=True)
    return None


def classify_url(url: str) -> tuple[str, str] | None:
    parsed = urlparse(url)
    if parsed.netloc and parsed.netloc not in (TVTROPES_DOMAIN, f"www.{TVTROPES_DOMAIN}"):
        return None
    m = PAGE_PATTERN.match(parsed.path)
    if not m:
        return None
    namespace, page_name = m.group(1), m.group(2)
    if namespace in SKIP_NAMESPACES:
        return None
    return namespace, page_name


def extract_page_links(soup: BeautifulSoup, base_url: str = TVTROPES_BASE) -> list[dict[str, str]]:
    links: list[dict[str, str]] = []
    seen = set()
    for a in soup.find_all("a", href=True):
        href: str = a["href"]
        full_url = urljoin(base_url, href)
        classified = classify_url(full_url)
        if classified is None:
            continue
        namespace, page_name = classified
        key = f"{namespace}/{page_name}"
        if key in seen:
            continue
        seen.add(key)
        links.append(
            {
                "url": full_url,
                "namespace": namespace,
                "page_name": page_name,
            }
        )
    return links


def is_work_namespace(namespace: str) -> bool:
    return namespace in {
        "Film",
        "Series",
        "Anime",
        "Literature",
        "VideoGame",
        "WesternAnimation",
        "Music",
        "ComicBook",
        "Webcomic",
        "WebOriginal",
        "Theatre",
        "VisualNovel",
        "Manga",
        "LightNovel",
        "Podcast",
        "Roleplay",
        "TabletopGame",
        "Radio",
        "Advertisement",
        "Franchise",
        "Creator",
    }


def split_trope_id(trope_id: str) -> tuple[str, str]:
    parts = trope_id.split("/", 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    return "Main", parts[0]


def extract_trope_links(soup: BeautifulSoup) -> list[dict[str, str]]:
    trope_links: list[dict[str, str]] = []
    seen = set()
    for a in soup.find_all("a", href=True):
        href: str = a["href"]
        full_url = urljoin(TVTROPES_BASE, href)
        classified = classify_url(full_url)
        if classified is None:
            continue
        namespace, page_name = classified
        if namespace == "Main":
            key = f"Main/{page_name}"
            if key not in seen:
                seen.add(key)
                trope_links.append(
                    {
                        "url": full_url,
                        "namespace": namespace,
                        "page_name": page_name,
                    }
                )
    return trope_links


def extract_work_trope_pairs(soup: BeautifulSoup) -> list[dict[str, str]]:
    pairs: list[dict[str, str]] = []
    seen = set()
    for a in soup.find_all("a", href=True):
        href: str = a["href"]
        full_url = urljoin(TVTROPES_BASE, href)
        classified = classify_url(full_url)
        if classified is None:
            continue
        ns, name = classified
        parent = a.find_parent(class_="grouptitle")
        if parent is None:
            parent = a.find_parent("div", class_="folder")
        key = f"{ns}/{name}"
        if key in seen:
            continue
        seen.add(key)
        if ns == "Main":
            pairs.append(
                {
                    "type": "trope",
                    "namespace": ns,
                    "page_name": name,
                }
            )
        elif is_work_namespace(ns):
            pairs.append(
                {
                    "type": "work",
                    "namespace": ns,
                    "page_name": name,
                }
            )
    return pairs


def extract_page_section(soup: BeautifulSoup, section_id: str) -> str | None:
    section = soup.find("div", id=section_id)
    if section:
        return section.get_text("\n", strip=True)
    return None


def extract_image_url(soup: BeautifulSoup) -> str | None:
    img = soup.find("img", class_="entry-image")
    if img and img.get("src"):
        src: str = img["src"]
        if src.startswith("//"):
            src = "https:" + src
        elif src.startswith("/"):
            src = urljoin(TVTROPES_BASE, src)
        return src
    return None


def parse_sitemap(xml_content: str) -> list[str]:
    soup = BeautifulSoup(xml_content, "xml")
    urls = []
    for loc in soup.find_all("loc"):
        text = loc.get_text(strip=True)
        if text and TVTROPES_DOMAIN in text:
            urls.append(text)
    return urls


def extract_page_metadata(soup: BeautifulSoup, url: str) -> dict[str, Any]:
    classified = classify_url(url)
    namespace = classified[0] if classified else None
    page_name = classified[1] if classified else None
    return {
        "namespace": namespace,
        "page_name": page_name,
        "title": extract_page_title(soup),
        "description": extract_page_description(soup),
        "laconic": extract_laconic(soup),
        "image_url": extract_image_url(soup),
        "page_links": extract_page_links(soup),
        "trope_links": extract_trope_links(soup),
        "is_work": is_work_namespace(namespace) if namespace else False,
    }


def extract_trope_from_html(html: str, url: str) -> dict[str, Any]:
    """Extract trope data from TVTropes HTML directly (no LLM needed).

    Returns same format as LLM extractor so it can be used as fallback.

    ## Return Format
    {"success": bool, "title": str, "description": str, "laconic": str|None,
     "examples": [], "related": [], "categories": []}
    """
    soup = BeautifulSoup(html, "lxml")
    meta = extract_page_metadata(soup, url)

    # Extract categories from page footer
    categories = []
    foldertags = soup.find("div", class_="foldertag")
    if foldertags:
        for a in foldertags.find_all("a"):
            categories.append(a.get_text(strip=True))

    # Extract related tropes from trope_links
    related = []
    for tl in meta.get("trope_links", []):
        related.append({
            "relation_type": "Related",
            "namespace": tl.get("namespace", "Main"),
            "page_name": tl.get("page_name", ""),
        })

    return {
        "success": True,
        "title": meta.get("title") or meta.get("page_name") or url,
        "description": meta.get("description") or "",
        "laconic": meta.get("laconic"),
        "examples": [],
        "related": related,
        "categories": categories,
        "_source": "html",
    }
