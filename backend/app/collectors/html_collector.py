from __future__ import annotations

from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from app.collectors.base import (
    CollectorOutcome,
    ExtractedDocumentPayload,
    check_robots_allowed,
    fetch_url_bytes,
    sha256_bytes,
)
from app.core.config import get_settings
from app.rag.chunker import extract_clean_html_text


def collect_official_html(
    url: str,
    *,
    title: str,
    scholarship_slug: str | None = None,
) -> CollectorOutcome:
    settings = get_settings()
    if not check_robots_allowed(url, settings.collector_user_agent):
        return CollectorOutcome(
            success=False,
            http_status=None,
            content_hash=None,
            summary="Blocked by robots.txt policy.",
            error_message=f"robots.txt disallows fetching {url}",
        )
    try:
        status_code, raw_bytes, content_type = fetch_url_bytes(url)
    except requests.RequestException as exc:
        return CollectorOutcome(
            success=False,
            http_status=getattr(getattr(exc, "response", None), "status_code", None),
            content_hash=None,
            summary="HTTP fetch failed.",
            error_message=str(exc),
        )

    html = raw_bytes.decode("utf-8", errors="replace")
    clean_text = extract_clean_html_text(html)
    content_hash = sha256_bytes(clean_text.encode("utf-8"))

    soup = BeautifulSoup(html, "lxml")
    pdf_urls: list[str] = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if ".pdf" in href.lower():
            abs_url = urljoin(url, href)
            if abs_url not in pdf_urls:
                pdf_urls.append(abs_url)

    doc = ExtractedDocumentPayload(
        scholarship_slug=scholarship_slug,
        title=title,
        source_url=url,
        document_type="html",
        content_hash=content_hash,
        pages=[(None, clean_text)],
    )
    return CollectorOutcome(
        success=True,
        http_status=status_code,
        content_hash=content_hash,
        summary=f"Fetched official HTML ({len(clean_text)} chars, {len(pdf_urls)} PDF link(s)).",
        documents=[doc],
        discovered_pdf_urls=pdf_urls[:25],
    )
