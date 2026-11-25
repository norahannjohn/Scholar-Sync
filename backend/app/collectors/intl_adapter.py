from __future__ import annotations

import re

from app.collectors.base import (
    CollectorOutcome,
    ExtractedScholarshipUpdate,
    compute_status_from_dates,
    parse_indian_date_str,
)
from app.collectors.html_collector import collect_official_html

INTL_SLUG_MAP = {
    "intl_campusfrance_eiffel": "france-excellence-eiffel-2027",
    "intl_csc_masters": "uk-commonwealth-masters",
    "intl_erasmus_mundus": "eu-erasmus-mundus-joint-masters",
    "intl_mext_japan": "japan-mext-government-scholarship",
    "intl_gates_cambridge": "uk-gates-cambridge",
    "intl_rhodes_india": "uk-rhodes-india",
    "intl_usief_fulbright": "us-fulbright-nehru-india",
}


def collect_intl_html_source(adapter_key: str, url: str, title: str) -> CollectorOutcome:
    """Collect live official international scholarship HTML pages and conservatively extract dates."""
    slug = INTL_SLUG_MAP.get(adapter_key)
    outcome = collect_official_html(url, title=title, scholarship_slug=slug)
    if not outcome.success or not outcome.documents or not slug:
        return outcome

    text = outcome.documents[0].pages[0][1]
    start_date = None
    deadline = None

    # Pattern for Campus France Eiffel ("Deadline for the reception of applications by Campus France: January 6, 2027")
    m_eiffel = re.search(
        r"Deadline for the reception of applications[^:]*:\s*([A-Za-z]+\s+\d{1,2},?\s+20\d{2}|\d{1,2}\s+[A-Za-z]+\s+20\d{2})",
        text,
        re.IGNORECASE,
    )
    if m_eiffel:
        deadline = parse_month_first_or_day_first(m_eiffel.group(1))

    # Pattern for Rhodes India ("Opening date: 1 June 2026 Closing date: ... 23 July 2026")
    m_open = re.search(
        r"Opening date:\s*(\d{1,2}\s+[A-Za-z]+\s+20\d{2})",
        text,
        re.IGNORECASE,
    )
    if m_open:
        start_date = parse_indian_date_str(m_open.group(1))

    m_close = re.search(
        r"Closing date:[^\d]*(\d{1,2}\s+[A-Za-z]+\s+20\d{2})",
        text,
        re.IGNORECASE,
    )
    if m_close:
        deadline = parse_indian_date_str(m_close.group(1))

    if start_date or deadline:
        st, reason = compute_status_from_dates(start_date, deadline)
        outcome.scholarship_updates.append(
            ExtractedScholarshipUpdate(
                slug=slug,
                application_start_date=start_date,
                application_deadline=deadline,
                status=st,
                status_reason=reason,
                confidence="high",
            )
        )

    return outcome


def parse_month_first_or_day_first(raw: str):
    from datetime import date

    from app.collectors.base import MONTH_MAP

    d = parse_indian_date_str(raw)
    if d:
        return d
    m = re.search(r"([A-Za-z]+)\s+(\d{1,2}),?\s+(20\d{2})", raw.strip(), re.IGNORECASE)
    if m:
        mo = MONTH_MAP.get(m.group(1).lower())
        day = int(m.group(2))
        yr = int(m.group(3))
        if mo:
            try:
                return date(yr, mo, day)
            except ValueError:
                return None
    return None
