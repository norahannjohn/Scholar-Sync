from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests

from app.core.config import get_settings


@dataclass
class ExtractedDocumentPayload:
    scholarship_slug: str | None
    title: str
    source_url: str
    document_type: str  # pdf | html | json
    content_hash: str
    pages: list[tuple[int | None, str]]
    document_version: str | None = None


@dataclass
class ExtractedScholarshipUpdate:
    slug: str
    application_start_date: date | None = None
    application_deadline: date | None = None
    status: str | None = None
    status_reason: str | None = None
    benefit_amount_display: str | None = None
    benefit_amount_inr: int | None = None
    official_application_url: str | None = None
    source_publication_date: date | None = None
    confidence: str = "high"  # high | partial


@dataclass
class CollectorOutcome:
    success: bool
    http_status: int | None
    content_hash: str | None
    summary: str
    error_message: str | None = None
    documents: list[ExtractedDocumentPayload] = field(default_factory=list)
    scholarship_updates: list[ExtractedScholarshipUpdate] = field(default_factory=list)
    discovered_pdf_urls: list[str] = field(default_factory=list)


MONTH_MAP = {
    "january": 1, "jan": 1,
    "february": 2, "feb": 2,
    "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "may": 5,
    "june": 6, "jun": 6,
    "july": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def check_robots_allowed(url: str, user_agent: str, timeout: int = 8) -> bool:
    """Respect robots.txt when fetching HTML pages."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return False
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    rp = RobotFileParser()
    try:
        resp = requests.get(robots_url, headers={"User-Agent": user_agent}, timeout=timeout)
        if resp.status_code == 200:
            rp.parse(resp.text.splitlines())
            return rp.can_fetch(user_agent, url)
        return True
    except requests.RequestException:
        return True


def fetch_url_bytes(url: str) -> tuple[int, bytes, str]:
    settings = get_settings()
    headers = {"User-Agent": settings.collector_user_agent}
    resp = requests.get(
        url,
        headers=headers,
        timeout=settings.collector_timeout_seconds,
        allow_redirects=True,
    )
    resp.raise_for_status()
    return resp.status_code, resp.content, resp.headers.get("Content-Type", "")


def parse_indian_date_str(text: str) -> date | None:
    """Parse common Indian official notification date formats conservatively."""
    if not text:
        return None
    # Pattern 1: DD.MM.YYYY or DD-MM-YYYY or DD/MM/YYYY
    m = re.search(r"\b(\d{1,2})[.\-/](\d{1,2})[.\-/](20\d{2})\b", text)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            return date(y, mo, d)
        except ValueError:
            pass
    # Pattern 2: 30th November 2026 / 15th March, 2027
    m2 = re.search(
        r"\b(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+),?\s+(20\d{2})\b",
        text,
        re.IGNORECASE,
    )
    if m2:
        d = int(m2.group(1))
        mo = MONTH_MAP.get(m2.group(2).lower())
        y = int(m2.group(3))
        if mo:
            try:
                return date(y, mo, d)
            except ValueError:
                pass
    return None


def compute_status_from_dates(
    start_date: date | None,
    deadline: date | None,
    today: date | None = None,
) -> tuple[str, str]:
    ref = today or datetime.now().date()
    if deadline is not None:
        if start_date is not None and ref < start_date:
            return "UPCOMING", f"Opens on {start_date.isoformat()} (closes {deadline.isoformat()})."
        if ref <= deadline:
            return "OPEN", f"Applications open until {deadline.isoformat()}."
        return "CLOSED", f"Deadline {deadline.isoformat()} has passed."
    if start_date is not None and ref < start_date:
        return "UPCOMING", f"Scheduled to open on {start_date.isoformat()}."
    return "UNKNOWN", "No confirmed closing date extracted from official source."
