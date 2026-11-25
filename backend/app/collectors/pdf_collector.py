from __future__ import annotations

import re

import pymupdf
import requests

from app.collectors.base import (
    CollectorOutcome,
    ExtractedDocumentPayload,
    ExtractedScholarshipUpdate,
    compute_status_from_dates,
    fetch_url_bytes,
    parse_indian_date_str,
    sha256_bytes,
)


def extract_pdf_pages(raw_bytes: bytes) -> list[tuple[int | None, str]]:
    doc = pymupdf.open(stream=raw_bytes, filetype="pdf")
    pages: list[tuple[int | None, str]] = []
    try:
        for i, page in enumerate(doc):
            txt = page.get_text("text").strip()
            if txt:
                pages.append((i + 1, txt))
    finally:
        doc.close()
    return pages


def extract_facts_from_pdf_text(
    full_text: str, slug: str
) -> ExtractedScholarshipUpdate | None:
    """Conservatively parse official dates & amounts from PDF notification text."""
    start_date = None
    deadline = None
    confidence = "partial"

    # Look for explicit opening phrases
    for pat in [
        r"Opening of portal[^\n]*?\n?\s*([0-9]{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]+,?\s+20\d{2})",
        r"Opening date of portal[^\n]*?\n?\s*([0-9]{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]+,?\s+20\d{2})",
    ]:
        m = re.search(pat, full_text, re.IGNORECASE)
        if m:
            start_date = parse_indian_date_str(m.group(1))
            if start_date:
                break

    # Look for explicit closing / extension / student last date phrases
    for pat in [
        r"extended\s+up\s*to\s+([0-9]{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]+,?\s+20\d{2}|[0-9]{1,2}[.\-/][0-9]{1,2}[.\-/]20\d{2})",
        r"Portal to be closed on\s+([0-9]{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]+,?\s+20\d{2})",
        r"Last date for online submission of application by the student\.?\s*\n?\s*([0-9]{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]+,?\s+20\d{2})",
        r"last date for submission of online applications is\s+([0-9]{1,2}[.\-/][0-9]{1,2}[.\-/]20\d{2})",
    ]:
        m = re.search(pat, full_text, re.IGNORECASE)
        if m:
            deadline = parse_indian_date_str(m.group(1))
            if deadline:
                confidence = "high"
                break

    if not start_date and not deadline:
        return None

    status_val, reason = compute_status_from_dates(start_date, deadline)
    return ExtractedScholarshipUpdate(
        slug=slug,
        application_start_date=start_date,
        application_deadline=deadline,
        status=status_val,
        status_reason=reason,
        confidence=confidence,
    )


def collect_official_pdf(
    url: str,
    *,
    title: str,
    scholarship_slug: str | None = None,
    document_version: str | None = None,
) -> CollectorOutcome:
    try:
        status_code, raw_bytes, _ = fetch_url_bytes(url)
    except requests.RequestException as exc:
        return CollectorOutcome(
            success=False,
            http_status=getattr(getattr(exc, "response", None), "status_code", None),
            content_hash=None,
            summary="PDF download failed.",
            error_message=str(exc),
        )

    try:
        pages = extract_pdf_pages(raw_bytes)
    except Exception as exc:
        return CollectorOutcome(
            success=False,
            http_status=status_code,
            content_hash=sha256_bytes(raw_bytes),
            summary="PDF parsing failed.",
            error_message=str(exc),
        )

    content_hash = sha256_bytes(raw_bytes)
    doc = ExtractedDocumentPayload(
        scholarship_slug=scholarship_slug,
        title=title,
        source_url=url,
        document_type="pdf",
        content_hash=content_hash,
        pages=pages,
        document_version=document_version,
    )
    updates: list[ExtractedScholarshipUpdate] = []
    if scholarship_slug and pages:
        combined = "\n".join(text for _, text in pages)
        fact = extract_facts_from_pdf_text(combined, scholarship_slug)
        if fact:
            updates.append(fact)

    return CollectorOutcome(
        success=True,
        http_status=status_code,
        content_hash=content_hash,
        summary=f"Extracted {len(pages)} PDF page(s) from official document.",
        documents=[doc],
        scholarship_updates=updates,
    )
