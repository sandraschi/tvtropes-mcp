"""Tests for content_extractor XSS hardening (PagesPage renders via dangerouslySetInnerHTML)."""

from __future__ import annotations

from tvtropes_mcp.content_extractor import extract_main_content


def test_script_tags_removed() -> None:
    html = "<html><body><div><p>Hello</p><script>alert(1)</script></div></body></html>"
    out = extract_main_content(html)
    assert "<script" not in out
    assert "Hello" in out


def test_event_handler_attributes_removed() -> None:
    html = (
        '<html><body><div><img src="x.png" onerror="alert(1)"><a href="/x" onclick="evil()">y</a></div></body></html>'
    )
    out = extract_main_content(html)
    assert "onerror" not in out
    assert "onclick" not in out


def test_javascript_urls_and_frames_removed() -> None:
    html = '<html><body><div><a href="javascript:alert(1)">x</a><iframe src="https://evil.example/"></iframe></div></body></html>'
    out = extract_main_content(html)
    assert "javascript:" not in out
    assert "<iframe" not in out
