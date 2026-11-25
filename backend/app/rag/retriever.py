from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.models.rag import GuidelineChunk, GuidelineDocument

STOP_WORDS = {
    "the", "is", "are", "for", "and", "or", "of", "to", "in", "a", "an",
    "on", "with", "what", "which", "how", "can", "i", "my", "this", "that",
    "scholarship", "scholarships", "be", "will", "from", "by", "as", "at",
}


@dataclass
class RetrievedPassage:
    chunk_id: str
    scholarship_id: str
    document_title: str
    source_url: str
    page_number: int | None
    section_heading: str | None
    verification_status: str
    retrieved_at: datetime
    excerpt: str
    score: float


def _tokenize(text_val: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9]{2,}", text_val.lower())
    return [t for t in tokens if t not in STOP_WORDS]


def _score_chunk_python(query_tokens: list[str], raw_query: str, content: str, heading: str | None) -> float:
    if not query_tokens:
        return 0.1
    content_lower = content.lower()
    heading_lower = (heading or "").lower()
    doc_tokens = _tokenize(content)
    if not doc_tokens:
        return 0.0
    freq: dict[str, int] = {}
    for tok in doc_tokens:
        freq[tok] = freq.get(tok, 0) + 1

    score = 0.0
    matched_terms = 0
    for q in set(query_tokens):
        tf = freq.get(q, 0)
        if tf > 0:
            matched_terms += 1
            score += 1.0 + math.log1p(tf)
        if q in heading_lower:
            score += 1.5
    if matched_terms == 0:
        return 0.0
    coverage = matched_terms / len(set(query_tokens))
    phrase_bonus = 2.0 if raw_query.strip().lower() in content_lower else 0.0
    return score * (0.5 + coverage) + phrase_bonus


def retrieve_passages(
    db: Session,
    query: str,
    scholarship_id: str | None = None,
    limit: int = 5,
) -> list[RetrievedPassage]:
    """Retrieve official guideline passages from PostgreSQL (FTS + Python reranking)."""
    stmt = (
        select(GuidelineChunk, GuidelineDocument.title)
        .join(GuidelineDocument, GuidelineChunk.document_id == GuidelineDocument.id)
    )
    if scholarship_id:
        stmt = stmt.where(GuidelineChunk.scholarship_id == scholarship_id)

    dialect = db.get_bind().dialect.name if db.get_bind() is not None else "sqlite"
    rows: list[tuple[GuidelineChunk, str]] = []

    if dialect == "postgresql" and query.strip():
        ts_query = func.plainto_tsquery("english", query)
        ts_vec = func.to_tsvector("english", GuidelineChunk.content)
        fts_stmt = (
            stmt.where(ts_vec.op("@@")(ts_query))
            .order_by(func.ts_rank(ts_vec, ts_query).desc())
            .limit(max(limit * 4, 20))
        )
        rows = list(db.execute(fts_stmt).all())

    if not rows:
        # Fallback to scanning candidate chunks for the scholarship (or latest indexed chunks)
        fallback_stmt = stmt.order_by(GuidelineChunk.chunk_index.asc()).limit(250)
        rows = list(db.execute(fallback_stmt).all())

    q_tokens = _tokenize(query)
    scored: list[RetrievedPassage] = []
    for chunk, doc_title in rows:
        score = _score_chunk_python(q_tokens, query, chunk.content, chunk.section_heading)
        if score <= 0 and q_tokens and not scholarship_id:
            continue
        scored.append(
            RetrievedPassage(
                chunk_id=chunk.id,
                scholarship_id=chunk.scholarship_id,
                document_title=doc_title,
                source_url=chunk.source_url,
                page_number=chunk.page_number,
                section_heading=chunk.section_heading,
                verification_status=chunk.verification_status,
                retrieved_at=chunk.retrieved_at,
                excerpt=chunk.content[:650],
                score=score,
            )
        )

    scored.sort(key=lambda item: item.score, reverse=True)
    if not scored and rows and scholarship_id:
        # Return leading passages from the scholarship's official document if query had no keyword overlap
        for chunk, doc_title in rows[:limit]:
            scored.append(
                RetrievedPassage(
                    chunk_id=chunk.id,
                    scholarship_id=chunk.scholarship_id,
                    document_title=doc_title,
                    source_url=chunk.source_url,
                    page_number=chunk.page_number,
                    section_heading=chunk.section_heading,
                    verification_status=chunk.verification_status,
                    retrieved_at=chunk.retrieved_at,
                    excerpt=chunk.content[:650],
                    score=0.0,
                )
            )

    return scored[:limit]


def index_guideline_document(
    db: Session,
    *,
    scholarship_id: str,
    title: str,
    provider: str,
    source_url: str,
    document_type: str,
    content_hash: str,
    pages: list[tuple[int | None, str]],
    verification_status: str,
    document_version: str | None = None,
) -> GuidelineDocument:
    """Replace/re-index chunks for a source document while preserving document metadata."""
    from app.models.user import utcnow
    from app.rag.chunker import chunk_pages

    existing = db.scalar(
        select(GuidelineDocument).where(
            GuidelineDocument.scholarship_id == scholarship_id,
            GuidelineDocument.source_url == source_url,
        )
    )
    now = utcnow()
    if existing and existing.content_hash == content_hash and existing.extraction_status == "INDEXED":
        existing.retrieved_at = now
        existing.verification_status = verification_status
        db.add(existing)
        db.flush()
        return existing

    if existing:
        db.execute(
            text("DELETE FROM guideline_chunks WHERE document_id = :doc_id"),
            {"doc_id": existing.id},
        )
        doc = existing
        doc.title = title
        doc.provider = provider
        doc.document_type = document_type
        doc.document_version = document_version
        doc.content_hash = content_hash
        doc.verification_status = verification_status
        doc.retrieved_at = now
    else:
        doc = GuidelineDocument(
            scholarship_id=scholarship_id,
            title=title,
            provider=provider,
            source_url=source_url,
            document_type=document_type,
            document_version=document_version,
            content_hash=content_hash,
            extraction_status="PENDING",
            verification_status=verification_status,
            retrieved_at=now,
        )
        db.add(doc)
        db.flush()

    chunks = chunk_pages(pages)
    if chunks:
        for ch in chunks:
            db.add(
                GuidelineChunk(
                    document_id=doc.id,
                    scholarship_id=scholarship_id,
                    chunk_index=ch.chunk_index,
                    section_heading=ch.section_heading,
                    page_number=ch.page_number,
                    content=ch.content,
                    source_url=source_url,
                    document_version=document_version,
                    verification_status=verification_status,
                    retrieved_at=now,
                )
            )
        doc.extraction_status = "INDEXED"
    else:
        doc.extraction_status = "FAILED"

    db.add(doc)
    db.flush()
    return doc
