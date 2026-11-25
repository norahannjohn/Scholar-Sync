from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.collectors.aicte_adapter import collect_aicte_source
from app.collectors.api_collector import collect_official_api
from app.collectors.base import CollectorOutcome, ExtractedScholarshipUpdate
from app.collectors.html_collector import collect_official_html
from app.collectors.intl_adapter import collect_intl_html_source
from app.collectors.pdf_collector import collect_official_pdf
from app.models.scholarship import (
    Scholarship,
    ScholarshipSource,
    ScholarshipVersion,
    SourceCheckLog,
)
from app.rag.retriever import index_guideline_document
from app.services.notification_service import notify_affected_users_of_scholarship_change


def _run_collector_for_source(source: ScholarshipSource) -> CollectorOutcome:
    if source.adapter_key and source.adapter_key.startswith("aicte_"):
        return collect_aicte_source(source.adapter_key, source.url, source.name)
    if source.adapter_key and source.adapter_key.startswith("intl_"):
        return collect_intl_html_source(source.adapter_key, source.url, source.name)
    if source.collection_method == "http_pdf" or source.source_type == "official_pdf":
        return collect_official_pdf(source.url, title=source.name)
    if source.collection_method == "http_json" or source.source_type == "official_api":
        return collect_official_api(source.url, title=source.name)
    if source.collection_method == "http_html" or source.source_type == "official_html":
        return collect_official_html(source.url, title=source.name)
    return CollectorOutcome(
        success=True,
        http_status=None,
        content_hash=source.last_content_hash,
        summary="Manual/admin source skipped during automated HTTP fetch.",
    )


def _apply_scholarship_update(
    db: Session,
    *,
    scholarship: Scholarship,
    update: ExtractedScholarshipUpdate,
    source: ScholarshipSource,
    now: datetime,
) -> bool:
    """Full Auto-Update: apply detected official changes & record immutable version history."""
    changed_fields: dict = {}

    def record_change(field_name: str, old_val: object, new_val: object) -> None:
        if new_val is not None and old_val != new_val:
            changed_fields[field_name] = {
                "old": old_val.isoformat() if hasattr(old_val, "isoformat") else old_val,
                "new": new_val.isoformat() if hasattr(new_val, "isoformat") else new_val,
            }
            setattr(scholarship, field_name, new_val)

    old_snapshot = {
        "name": scholarship.name,
        "status": scholarship.status,
        "status_reason": scholarship.status_reason,
        "application_start_date": scholarship.application_start_date.isoformat()
        if scholarship.application_start_date
        else None,
        "application_deadline": scholarship.application_deadline.isoformat()
        if scholarship.application_deadline
        else None,
        "benefit_amount_display": scholarship.benefit_amount_display,
        "benefit_amount_inr": scholarship.benefit_amount_inr,
        "official_application_url": scholarship.official_application_url,
    }

    record_change("application_start_date", scholarship.application_start_date, update.application_start_date)
    record_change("application_deadline", scholarship.application_deadline, update.application_deadline)
    record_change("status", scholarship.status, update.status)
    record_change("status_reason", scholarship.status_reason, update.status_reason)
    record_change("benefit_amount_display", scholarship.benefit_amount_display, update.benefit_amount_display)
    record_change("benefit_amount_inr", scholarship.benefit_amount_inr, update.benefit_amount_inr)
    record_change("official_application_url", scholarship.official_application_url, update.official_application_url)
    record_change("source_publication_date", scholarship.source_publication_date, update.source_publication_date)

    scholarship.last_checked_at = now
    if update.confidence == "high":
        scholarship.last_verified_at = now
        scholarship.verification_state = "VERIFIED"
    elif changed_fields:
        scholarship.verification_state = "NEEDS_REVIEW"

    if not changed_fields:
        db.add(scholarship)
        return False

    scholarship.current_version += 1
    db.add(scholarship)
    db.flush()

    db.add(
        ScholarshipVersion(
            scholarship_id=scholarship.id,
            version_number=scholarship.current_version,
            snapshot=old_snapshot,
            changed_fields=changed_fields,
            change_source=f"auto_collector:{source.adapter_key or source.collection_method}",
            source_url=source.url,
            reviewed=update.confidence == "high",
            reviewed_by="auto_collector" if update.confidence == "high" else None,
            reviewed_at=now if update.confidence == "high" else None,
        )
    )
    notify_affected_users_of_scholarship_change(
        db, scholarship=scholarship, changed_fields=changed_fields
    )
    return True


def sync_single_source(
    db: Session,
    source: ScholarshipSource,
    *,
    stale_after_days: int = 14,
) -> dict:
    now = datetime.now(UTC)
    outcome = _run_collector_for_source(source)
    source.last_checked_at = now

    change_detected = False
    scholarships_updated = 0
    documents_reindexed = 0

    if outcome.success:
        if outcome.content_hash and source.last_content_hash and outcome.content_hash != source.last_content_hash:
            change_detected = True
        elif outcome.content_hash and not source.last_content_hash:
            change_detected = True

        source.last_content_hash = outcome.content_hash
        source.last_successful_at = now
        source.last_error = None

        for doc_payload in outcome.documents:
            if not doc_payload.scholarship_slug:
                continue
            schol = db.scalar(
                select(Scholarship).where(Scholarship.slug == doc_payload.scholarship_slug)
            )
            if not schol:
                continue
            schol.last_checked_at = now
            if schol.verification_state == "STALE":
                schol.verification_state = "VERIFIED"
            index_guideline_document(
                db,
                scholarship_id=schol.id,
                title=doc_payload.title,
                provider=schol.provider,
                source_url=doc_payload.source_url,
                document_type=doc_payload.document_type,
                content_hash=doc_payload.content_hash,
                pages=doc_payload.pages,
                verification_status=schol.verification_state,
                document_version=doc_payload.document_version,
            )
            documents_reindexed += 1

        for upd in outcome.scholarship_updates:
            schol = db.scalar(select(Scholarship).where(Scholarship.slug == upd.slug))
            if not schol:
                continue
            if _apply_scholarship_update(db, scholarship=schol, update=upd, source=source, now=now):
                scholarships_updated += 1
                change_detected = True

        linked = list(
            db.scalars(select(Scholarship).where(Scholarship.source_id == source.id)).all()
        )
        for schol in linked:
            schol.last_checked_at = now
            if schol.verification_state == "STALE":
                schol.verification_state = "VERIFIED"
            db.add(schol)
    else:
        source.last_error = outcome.error_message
        linked = list(
            db.scalars(select(Scholarship).where(Scholarship.source_id == source.id)).all()
        )
        for schol in linked:
            if schol.last_verified_at:
                last_ver = schol.last_verified_at
                if last_ver.tzinfo is None:
                    last_ver = last_ver.replace(tzinfo=UTC)
                age_days = (now - last_ver).days
                if age_days >= stale_after_days:
                    schol.verification_state = "STALE"
                    db.add(schol)

    db.add(source)
    db.add(
        SourceCheckLog(
            source_id=source.id,
            checked_at=now,
            http_status=outcome.http_status,
            success=outcome.success,
            content_hash=outcome.content_hash,
            change_detected=change_detected,
            auto_updated_count=scholarships_updated,
            summary=outcome.summary,
            error_message=outcome.error_message,
        )
    )
    db.commit()

    return {
        "source_id": source.id,
        "source_name": source.name,
        "url": source.url,
        "success": outcome.success,
        "http_status": outcome.http_status,
        "change_detected": change_detected,
        "scholarships_updated": scholarships_updated,
        "documents_reindexed": documents_reindexed,
        "summary": outcome.summary,
        "error": outcome.error_message,
    }


def sync_all_active_sources(db: Session, *, stale_after_days: int = 14) -> dict:
    sources = list(
        db.scalars(select(ScholarshipSource).where(ScholarshipSource.is_active.is_(True))).all()
    )
    details: list[dict] = []
    succeeded = 0
    failed = 0
    changes = 0
    schol_updates = 0
    docs_reindexed = 0

    for src in sources:
        res = sync_single_source(db, src, stale_after_days=stale_after_days)
        details.append(res)
        if res["success"]:
            succeeded += 1
        else:
            failed += 1
        if res["change_detected"]:
            changes += 1
        schol_updates += res["scholarships_updated"]
        docs_reindexed += res["documents_reindexed"]

    return {
        "sources_checked": len(sources),
        "sources_succeeded": succeeded,
        "sources_failed": failed,
        "changes_detected": changes,
        "scholarships_updated": schol_updates,
        "documents_reindexed": docs_reindexed,
        "details": details,
    }
