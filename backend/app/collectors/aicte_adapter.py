from __future__ import annotations

import hashlib

from app.collectors.base import (
    CollectorOutcome,
    ExtractedDocumentPayload,
    ExtractedScholarshipUpdate,
    compute_status_from_dates,
)
from app.collectors.html_collector import collect_official_html
from app.collectors.pdf_collector import collect_official_pdf, extract_facts_from_pdf_text

# Official AICTE document mapping verified from aicte.gov.in
AICTE_PDF_TARGETS: dict[str, list[dict]] = {
    "aicte_nsp_extension_2026": [
        {
            "slug": "aicte-pragati-degree",
            "title": "AICTE Pragati / Saksham / Swanath Date Extension Notification (A/Y 2026-27)",
            "url": "https://aicte.gov.in/downloads/schemes/Notification%20of%20Date%20Extended%20on%20NSP.pdf",
        },
        {
            "slug": "aicte-saksham-degree",
            "title": "AICTE Pragati / Saksham / Swanath Date Extension Notification (A/Y 2026-27)",
            "url": "https://aicte.gov.in/downloads/schemes/Notification%20of%20Date%20Extended%20on%20NSP.pdf",
        },
        {
            "slug": "aicte-swanath",
            "title": "AICTE Pragati / Saksham / Swanath Date Extension Notification (A/Y 2026-27)",
            "url": "https://aicte.gov.in/downloads/schemes/Notification%20of%20Date%20Extended%20on%20NSP.pdf",
        },
    ],
    "aicte_pragati_guidelines": [
        {
            "slug": "aicte-pragati-degree",
            "title": "AICTE Pragati Scholarship Scheme Guidelines (Degree)",
            "url": "https://www.aicte.gov.in/sites/default/files/stdc/Pragati/AICTE%20Pragati%20Scheme%20Guidelines_Degree.pdf",
        }
    ],
    "aicte_saksham_guidelines": [
        {
            "slug": "aicte-saksham-degree",
            "title": "AICTE Saksham Scholarship Scheme Guidelines (Degree)",
            "url": "https://www.aicte.gov.in/sites/default/files/stdc/AICTE%20Saksham%20Scheme%20Guidelines_Degree.pdf",
        }
    ],
    "aicte_swanath_guidelines": [
        {
            "slug": "aicte-swanath",
            "title": "AICTE Swanath Scholarship Scheme Guidelines (May 2025)",
            "url": "https://www.aicte.gov.in/sites/default/files/AICTE-SWANATH.pdf",
        }
    ],
    "aicte_pg_2026": [
        {
            "slug": "aicte-pg-scholarship",
            "title": "AICTE Post Graduate (PG) Scholarship Notification A/Y 2026-27",
            "url": "https://aicte.gov.in/downloads/pg/Flag-A-Notification%202026-27.pdf",
        }
    ],
    "aicte_pg_guidelines": [
        {
            "slug": "aicte-pg-scholarship",
            "title": "AICTE Post Graduate (PG) Scholarship Guidelines",
            "url": "https://www.aicte.gov.in/sites/default/files/stdc/PG%20scheme%20guidelines%20(2023-24).pdf",
        }
    ],
    "aicte_saraswati_2026": [
        {
            "slug": "aicte-saraswati-2026-27",
            "title": "AICTE Saraswati Scholarship Scheme Notification A/Y 2026-27",
            "url": "https://aicte.gov.in/downloads/schemes/Sarswati%20Notification%202026-27.pdf",
        }
    ],
    "aicte_yashasvi_2026": [
        {
            "slug": "aicte-yashasvi-2026-27",
            "title": "AICTE Yashasvi Scholarship Scheme Notification A/Y 2026-27",
            "url": "https://aicte.gov.in/downloads/schemes/Yashasvi%20Notification%202026-27.pdf",
        }
    ],
    "aicte_samarthan_guidelines": [
        {
            "slug": "aicte-samarthan",
            "title": "AICTE SAMARTHAN Internship Connect Scheme Document",
            "url": "https://aicte.gov.in/downloads/schemes/Scheme%20Guidlines%20SAMARTHAN.pdf",
        }
    ],
    "aicte_apdf_2026": [
        {
            "slug": "aicte-apdf-2026",
            "title": "AICTE Post-Doctoral Fellowship (APDF) Revised Guidelines 2026",
            "url": "https://aicte.gov.in/downloads/schemes/APDF%20revised%20scheme%20guidelines%202026.pdf",
        }
    ],
}


def collect_aicte_source(adapter_key: str, url: str, title: str) -> CollectorOutcome:
    """Collect live updates from official AICTE portals and notification PDFs."""
    if adapter_key == "aicte_portal_hub":
        return collect_official_html(url, title=title)

    targets = AICTE_PDF_TARGETS.get(adapter_key)
    if not targets:
        return collect_official_pdf(url, title=title)

    # Fetch the shared official PDF once and apply updates to all mapped schemes
    primary_url = targets[0]["url"]
    base_outcome = collect_official_pdf(
        primary_url,
        title=targets[0]["title"],
        scholarship_slug=targets[0]["slug"],
    )
    if not base_outcome.success or not base_outcome.documents:
        return base_outcome

    base_doc = base_outcome.documents[0]
    combined_text = "\n".join(text for _, text in base_doc.pages)

    docs: list[ExtractedDocumentPayload] = []
    updates: list[ExtractedScholarshipUpdate] = []
    for target in targets:
        slug = target["slug"]
        docs.append(
            ExtractedDocumentPayload(
                scholarship_slug=slug,
                title=target["title"],
                source_url=target["url"],
                document_type="pdf",
                content_hash=hashlib.sha256(
                    f"{slug}:{base_doc.content_hash}".encode()
                ).hexdigest(),
                pages=base_doc.pages,
                document_version="2026-27",
            )
        )
        fact = extract_facts_from_pdf_text(combined_text, slug)
        if fact:
            # Ensure status is freshly computed from extracted dates
            st, reason = compute_status_from_dates(
                fact.application_start_date, fact.application_deadline
            )
            fact.status = st
            fact.status_reason = reason
            updates.append(fact)

    return CollectorOutcome(
        success=True,
        http_status=base_outcome.http_status,
        content_hash=base_outcome.content_hash,
        summary=(
            f"Verified {len(base_doc.pages)} official PDF page(s); "
            f"extracted {len(updates)} scheme date/status update(s)."
        ),
        documents=docs,
        scholarship_updates=updates,
    )
