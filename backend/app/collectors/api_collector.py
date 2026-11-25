from __future__ import annotations

import json

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


def collect_official_api(url: str, *, title: str) -> CollectorOutcome:
    """Adapter for permitted public JSON/API endpoints returning structured scheme records."""
    try:
        status_code, raw_bytes, _ = fetch_url_bytes(url)
    except requests.RequestException as exc:
        return CollectorOutcome(
            success=False,
            http_status=getattr(getattr(exc, "response", None), "status_code", None),
            content_hash=None,
            summary="Public API fetch failed.",
            error_message=str(exc),
        )

    content_hash = sha256_bytes(raw_bytes)
    try:
        payload = json.loads(raw_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return CollectorOutcome(
            success=False,
            http_status=status_code,
            content_hash=content_hash,
            summary="Invalid JSON payload from endpoint.",
            error_message=str(exc),
        )

    records = payload if isinstance(payload, list) else payload.get("schemes", [])
    updates: list[ExtractedScholarshipUpdate] = []
    docs: list[ExtractedDocumentPayload] = []

    if isinstance(records, list):
        for item in records:
            if not isinstance(item, dict) or not item.get("slug"):
                continue
            slug = str(item["slug"])
            start_d = parse_indian_date_str(str(item.get("application_start_date") or ""))
            end_d = parse_indian_date_str(str(item.get("application_deadline") or ""))
            status_val, reason = compute_status_from_dates(start_d, end_d)
            updates.append(
                ExtractedScholarshipUpdate(
                    slug=slug,
                    application_start_date=start_d,
                    application_deadline=end_d,
                    status=item.get("status") or status_val,
                    status_reason=item.get("status_reason") or reason,
                    benefit_amount_display=item.get("benefit_amount_display"),
                    benefit_amount_inr=item.get("benefit_amount_inr"),
                    official_application_url=item.get("official_application_url"),
                    confidence="high",
                )
            )
        docs.append(
            ExtractedDocumentPayload(
                scholarship_slug=None,
                title=title,
                source_url=url,
                document_type="json",
                content_hash=content_hash,
                pages=[(None, json.dumps(records, indent=2)[:8000])],
            )
        )

    return CollectorOutcome(
        success=True,
        http_status=status_code,
        content_hash=content_hash,
        summary=f"Parsed {len(updates)} structured record(s) from public API.",
        documents=docs,
        scholarship_updates=updates,
    )
