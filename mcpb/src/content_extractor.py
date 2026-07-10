"""Extract the main body content from a TVTropes cached HTML page."""

from __future__ import annotations

from bs4 import BeautifulSoup


def extract_main_content(html: str) -> str:
    """Extract the main article body from a TVTropes HTML page.

    Strips navigation, sidebar, footer, header, and the 'folder' sections
    (which contain the trope example list at the bottom).
    Returns clean HTML of just the main body.
    """
    soup = BeautifulSoup(html, "lxml")

    # Remove unwanted sections
    for selector in [
        "nav", "footer", "header", "aside",
        "script", "style", "noscript",
        "#sidebar", "#nav", "#footer", "#header",
        ".footer", ".nav", ".sidebar", ".header",
        ".advertisement", ".ad", ".ads",
        ".folder",  # trope example sections
        ".grouptitle",
        ".platform",  # platform metadata
        ".page-actions",
        ".breadcrumb",
    ]:
        for tag in soup.select(selector):
            tag.decompose()

    # Try multiple content area selectors
    for selector in [
        "#main-article",
        "#main-content",
        "#main",
        ".entry-content",
        ".content",
        "article",
        "[role=main]",
        "body",
    ]:
        main = soup.select_one(selector)
        if main:
            # If we got body, extract only meaningful children
            if main.name == "body":
                children = main.find_all(["div", "article", "section"], recursive=False)
                if children:
                    return "".join(str(c) for c in children[:3])
            return str(main)

    return str(soup.body) if soup.body else html[:5000]


def extract_text_only(html: str, max_chars: int = 5000) -> str:
    """Extract plain text from the main content, stripped of HTML tags."""
    main_html = extract_main_content(html)
    soup = BeautifulSoup(main_html, "lxml")
    text = soup.get_text(separator="\n", strip=True)
    return text[:max_chars]
