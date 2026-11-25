from __future__ import annotations

import ipaddress
import re
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urljoin, urlparse

import pymupdf
import requests
from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.collectors.base import check_robots_allowed
from app.core.config import get_settings
from app.models.scholarship import ScholarshipSource
from app.rag.chunker import extract_clean_html_text

# Official domain suffixes & vetted official scholarship domains for safe live discovery
ALLOWED_OFFICIAL_SUFFIXES = (
    ".gov.in",
    ".nic.in",
    ".ac.in",
    ".edu.in",
    ".gov.uk",
    ".ac.uk",
    ".europa.eu",
    ".go.jp",
    ".edu",
    ".gov",
    ".gov.au",
    ".gc.ca",
)

ALLOWED_OFFICIAL_HOSTS = {
    "www.campusfrance.org",
    "campusfrance.org",
    "www.gatescambridge.org",
    "gatescambridge.org",
    "www.rhodeshouse.ox.ac.uk",
    "rhodeshouse.ox.ac.uk",
    "usief.org.in",
    "www.usief.org.in",
    "www.chevening.org",
    "chevening.org",
    "www.daad.de",
    "daad.de",
    "www.daad.in",
    "daad.in",
    "www.britishcouncil.in",
    "www.britishcouncil.org",
    "www.studyinjapan.go.jp",
}

OFFICIAL_PORTAL_DIRECTORY: list[dict[str, Any]] = [
    {
        "title": "AICTE Student Development Schemes (India)",
        "url": "https://www.aicte.gov.in/schemes/students-development-schemes",
        "scope": "india",
        "countries": ["India"],
        "levels": ["diploma", "undergraduate", "postgraduate", "doctoral"],
        "keywords": ["india", "aicte", "pragati", "saksham", "swanath", "pg", "yashasvi", "saraswati", "engineering", "technical", "gate", "girl"],
    },
    {
        "title": "UGC Scholarships & Fellowships Portal (India)",
        "url": "https://www.ugc.gov.in/Scholarships",
        "scope": "india",
        "countries": ["India"],
        "levels": ["undergraduate", "postgraduate", "doctoral"],
        "keywords": ["india", "ugc", "ishan uday", "single girl", "university", "fellowship", "postgraduate"],
    },
    {
        "title": "Campus France — Eiffel Excellence Scholarship Program (France)",
        "url": "https://www.campusfrance.org/en/france-excellence-eiffel-scholarship-program",
        "scope": "international_abroad",
        "countries": ["France", "Europe", "European Union"],
        "levels": ["postgraduate", "doctoral"],
        "keywords": ["france", "eiffel", "europe", "master", "phd", "abroad", "international", "full", "stipend", "engineering", "management"],
    },
    {
        "title": "Commonwealth Master's Scholarships (UK FCDO / CSC)",
        "url": "https://cscuk.fcdo.gov.uk/scholarships/commonwealth-masters-scholarships/",
        "scope": "international_abroad",
        "countries": ["United Kingdom", "UK"],
        "levels": ["postgraduate"],
        "keywords": ["uk", "united kingdom", "britain", "commonwealth", "master", "postgraduate", "abroad", "full", "fully funded", "india"],
    },
    {
        "title": "Commonwealth Shared Scholarships (UK FCDO / CSC)",
        "url": "https://cscuk.fcdo.gov.uk/scholarships/commonwealth-shared-scholarships-applications/",
        "scope": "international_abroad",
        "countries": ["United Kingdom", "UK"],
        "levels": ["postgraduate"],
        "keywords": ["uk", "united kingdom", "commonwealth", "shared", "master", "full", "abroad"],
    },
    {
        "title": "Gates Cambridge Scholarship Eligibility (University of Cambridge, UK)",
        "url": "https://www.gatescambridge.org/apply/eligibility/",
        "scope": "international_abroad",
        "countries": ["United Kingdom", "UK"],
        "levels": ["postgraduate", "doctoral"],
        "keywords": ["uk", "united kingdom", "cambridge", "gates", "phd", "master", "postgraduate", "full", "university"],
    },
    {
        "title": "The Rhodes Scholarships for India (University of Oxford, UK)",
        "url": "https://www.rhodeshouse.ox.ac.uk/scholarships/applications/india/",
        "scope": "international_abroad",
        "countries": ["United Kingdom", "UK"],
        "levels": ["postgraduate", "doctoral"],
        "keywords": ["uk", "united kingdom", "oxford", "rhodes", "india", "postgraduate", "master", "phd", "full"],
    },
    {
        "title": "European Commission — Erasmus Mundus Joint Masters (EU)",
        "url": "https://erasmus-plus.ec.europa.eu/opportunities/individuals/students/erasmus-mundus-joint-masters",
        "scope": "international_abroad",
        "countries": ["European Union", "Europe", "Germany", "France", "Netherlands", "Italy", "Spain"],
        "levels": ["postgraduate"],
        "keywords": ["europe", "eu", "erasmus", "mundus", "germany", "france", "netherlands", "italy", "spain", "master", "full", "abroad"],
    },
    {
        "title": "Study in Japan — MEXT Japanese Government Scholarships (Japan)",
        "url": "https://www.studyinjapan.go.jp/en/planning/scholarships/mext-scholarships/",
        "scope": "international_abroad",
        "countries": ["Japan"],
        "levels": ["undergraduate", "postgraduate", "doctoral", "diploma"],
        "keywords": ["japan", "mext", "tokyo", "research", "undergraduate", "master", "phd", "full", "abroad"],
    },
    {
        "title": "USIEF — Fulbright-Nehru Fellowships for Indian Citizens (United States)",
        "url": "https://usief.org.in/",
        "scope": "international_abroad",
        "countries": ["United States", "USA", "US"],
        "levels": ["postgraduate", "doctoral"],
        "keywords": ["usa", "us", "united states", "america", "fulbright", "usief", "master", "phd", "fellowship", "full", "abroad"],
    },
]


def _is_private_or_local_host(hostname: str) -> bool:
    if not hostname:
        return True
    lower = hostname.lower()
    if lower in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
        return True
    try:
        ip = ipaddress.ip_address(lower)
        return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
    except ValueError:
        pass
    try:
        resolved = socket.gethostbyname(lower)
        ip = ipaddress.ip_address(resolved)
        return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
    except OSError:
        # DNS resolution unavailable (e.g., offline sandbox) — suffix check handles safety
        return False


def is_safe_official_url(url: str, registered_hosts: set[str] | None = None) -> bool:
    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return False
    host = parsed.hostname.lower()
    if _is_private_or_local_host(host):
        return False
    if registered_hosts and host in registered_hosts:
        return True
    if host in ALLOWED_OFFICIAL_HOSTS:
        return True
    return any(host.endswith(suffix) for suffix in ALLOWED_OFFICIAL_SUFFIXES)


def _extract_relevant_excerpt(text: str, query: str, max_len: int = 750) -> str:
    if not text:
        return ""
    tokens = [t for t in re.findall(r"[a-z0-9]{3,}", query.lower())]
    paragraphs = [p.strip() for p in text.splitlines() if len(p.strip()) >= 25]
    if not paragraphs:
        return text[:max_len]

    scored: list[tuple[int, str]] = []
    for p in paragraphs[:120]:
        pl = p.lower()
        hits = sum(1 for tok in set(tokens) if tok in pl)
        if any(w in pl for w in ("eligib", "deadline", "closing", "opening", "funding", "scholarship", "fellowship", "tuition", "stipend", "indian", "citizen")):
            hits += 1
        scored.append((hits, p))
    scored.sort(key=lambda x: x[0], reverse=True)
    selected = [p for _, p in scored[:4]]
    joined = "\n".join(selected)
    return joined[:max_len]


def fetch_and_verify_official_url(
    url: str,
    *,
    title: str = "",
    query: str = "",
    registered_hosts: set[str] | None = None,
) -> dict[str, Any]:
    """Live-fetch a single safe official URL (HTML or PDF) and extract verifiable evidence."""
    checked_at = datetime.now(UTC)
    if not is_safe_official_url(url, registered_hosts):
        return {
            "title": title or url,
            "url": url,
            "http_status": None,
            "verified_live": False,
            "checked_at": checked_at,
            "excerpt": None,
            "discovered_links": [],
            "error": "URL is not on a recognized official or registered scholarship domain.",
        }

    settings = get_settings()
    if not check_robots_allowed(url, settings.collector_user_agent, timeout=5):
        return {
            "title": title or url,
            "url": url,
            "http_status": None,
            "verified_live": False,
            "checked_at": checked_at,
            "excerpt": None,
            "discovered_links": [],
            "error": "Blocked by site robots.txt policy.",
        }

    try:
        resp = requests.get(
            url,
            headers={"User-Agent": settings.collector_user_agent},
            timeout=settings.web_discovery_timeout_seconds,
            allow_redirects=True,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        return {
            "title": title or url,
            "url": url,
            "http_status": getattr(getattr(exc, "response", None), "status_code", None),
            "verified_live": False,
            "checked_at": checked_at,
            "excerpt": None,
            "discovered_links": [],
            "error": f"{type(exc).__name__}: {exc}",
        }

    content_type = resp.headers.get("Content-Type", "").lower()
    final_url = resp.url
    if ".pdf" in final_url.lower() or "application/pdf" in content_type:
        try:
            doc = pymupdf.open(stream=resp.content, filetype="pdf")
            try:
                pages_txt = []
                for idx, page in enumerate(doc[:5]):
                    txt = page.get_text("text").strip()
                    if txt:
                        pages_txt.append(f"[Page {idx + 1}] {txt}")
                combined = "\n".join(pages_txt)
            finally:
                doc.close()
            excerpt = _extract_relevant_excerpt(combined, query)
            return {
                "title": title or final_url.split("/")[-1],
                "url": final_url,
                "http_status": resp.status_code,
                "verified_live": True,
                "checked_at": checked_at,
                "excerpt": excerpt,
                "discovered_links": [],
                "error": None,
            }
        except Exception as exc:
            return {
                "title": title or final_url,
                "url": final_url,
                "http_status": resp.status_code,
                "verified_live": False,
                "checked_at": checked_at,
                "excerpt": None,
                "discovered_links": [],
                "error": f"PDF parse failed: {exc}",
            }

    html = resp.content.decode("utf-8", errors="replace")
    soup = BeautifulSoup(html, "lxml")
    page_title = title or (soup.title.get_text(" ", strip=True) if soup.title else final_url)
    clean_text = extract_clean_html_text(html)
    excerpt = _extract_relevant_excerpt(clean_text, query)

    discovered_links: list[dict[str, str]] = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        label = " ".join(a.get_text(" ", strip=True).split())
        if not label and ".pdf" not in href.lower():
            continue
        abs_link = urljoin(final_url, href)
        if not is_safe_official_url(abs_link, registered_hosts):
            continue
        if any(
            k in (label + " " + abs_link).lower()
            for k in ("eligib", "apply", "guideline", "deadline", "scholarship", "fellowship", "notification", ".pdf")
        ):
            if not any(x["url"] == abs_link for x in discovered_links):
                discovered_links.append({"label": label[:90] or "Official link", "url": abs_link})
        if len(discovered_links) >= 5:
            break

    return {
        "title": page_title[:160],
        "url": final_url,
        "http_status": resp.status_code,
        "verified_live": True,
        "checked_at": checked_at,
        "excerpt": excerpt,
        "discovered_links": discovered_links,
        "error": None,
    }


def extract_query_intent(message: str) -> dict[str, Any]:
    """Parse natural-language scholarship intent cleanly for deterministic & web discovery."""
    msg = message.lower()
    scope = ""
    if any(w in msg for w in ("abroad", "overseas", "foreign", "international", "study in ")):
        scope = "international_abroad"
    elif any(w in msg for w in ("in india", "aicte", "nsp", "ugc", "indian college")):
        scope = "india"

    country_aliases = {
        "United Kingdom": ["uk", "united kingdom", "britain", "england", "oxford", "cambridge"],
        "United States": ["usa", "us ", "united states", "america", "fulbright"],
        "France": ["france", "french", "eiffel", "paris"],
        "Germany": ["germany", "german", "daad"],
        "European Union": ["europe", "european", "erasmus", "eu "],
        "Japan": ["japan", "japanese", "mext"],
        "India": ["india", "aicte", "nsp", "ugc", "indian government"],
    }
    matched_countries: list[str] = []
    for country, keys in country_aliases.items():
        if any(k in msg for k in keys):
            matched_countries.append(country)
            if country != "India" and not scope:
                scope = "international_abroad"

    level = ""
    if any(w in msg for w in ("phd", "doctoral", "postdoc", "post-doc", "research")):
        level = "doctoral"
    elif any(w in msg for w in ("master", "postgraduate", "m.tech", "m.e", "mba", "msc", "pg ")):
        level = "postgraduate"
    elif any(w in msg for w in ("bachelor", "undergraduate", "b.tech", "b.e", "bca", "bba", "ug ")):
        level = "undergraduate"
    elif "diploma" in msg:
        level = "diploma"

    funding = ""
    if any(w in msg for w in ("full", "fully funded", "100%", "tuition and living")):
        funding = "full_funding"

    return {
        "study_scope": scope,
        "destination_countries": matched_countries,
        "education_level": level,
        "funding_type": funding,
    }


def discover_and_verify_official_sites(
    db: Session,
    *,
    query: str,
    destination_country: str = "",
    education_level: str = "",
    study_scope: str = "",
    max_sites: int = 4,
) -> dict[str, Any]:
    """Actively search & live-verify matching official scholarship websites."""
    settings = get_settings()
    if not settings.allow_live_web_discovery:
        return {
            "live_web_enabled": False,
            "verified_results": [],
            "unreachable_results": [],
            "note": "Live external web discovery disabled in current environment.",
        }

    registered_sources = list(
        db.scalars(select(ScholarshipSource).where(ScholarshipSource.is_active.is_(True))).all()
    )
    registered_hosts = {
        urlparse(s.url).hostname.lower()
        for s in registered_sources
        if urlparse(s.url).hostname
    }

    q_lower = query.lower()
    dest_lower = destination_country.strip().lower()
    level_lower = education_level.strip().lower()
    scope_lower = study_scope.strip().lower()

    candidates: list[tuple[int, dict[str, Any]]] = []
    seen_urls: set[str] = set()

    for entry in OFFICIAL_PORTAL_DIRECTORY:
        score = 0
        if scope_lower and entry["scope"] == scope_lower:
            score += 3
        if dest_lower and any(dest_lower in c.lower() for c in entry["countries"]):
            score += 6
        if level_lower and level_lower in entry["levels"]:
            score += 2
        for kw in entry["keywords"]:
            if kw in q_lower:
                score += 2
        candidates.append((score, {"title": entry["title"], "url": entry["url"]}))
        seen_urls.add(entry["url"])

    for src in registered_sources:
        if src.url in seen_urls:
            continue
        score = 0
        name_lower = (src.name + " " + src.owner_provider).lower()
        for tok in re.findall(r"[a-z0-9]{3,}", q_lower):
            if tok in name_lower:
                score += 2
        if dest_lower and dest_lower in name_lower:
            score += 4
        if score > 0:
            candidates.append((score, {"title": src.name, "url": src.url}))
            seen_urls.add(src.url)

    candidates.sort(key=lambda x: x[0], reverse=True)
    selected = [item for sc, item in candidates if sc > 0][:max_sites]
    if not selected:
        # Default broad mix of official domestic + international hubs
        selected = [item for _, item in candidates[:min(3, len(candidates))]]

    verified_results: list[dict[str, Any]] = []
    unreachable_results: list[dict[str, Any]] = []

    with ThreadPoolExecutor(max_workers=min(4, max(1, len(selected)))) as pool:
        futures = {
            pool.submit(
                fetch_and_verify_official_url,
                item["url"],
                title=item["title"],
                query=query,
                registered_hosts=registered_hosts,
            ): item
            for item in selected
        }
        for fut in as_completed(futures):
            res = fut.result()
            if res["verified_live"]:
                verified_results.append(res)
            else:
                unreachable_results.append(res)

    return {
        "live_web_enabled": True,
        "sites_queried": len(selected),
        "verified_results": verified_results,
        "unreachable_results": unreachable_results,
    }
