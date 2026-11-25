from __future__ import annotations

from datetime import UTC, datetime
from math import ceil

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.eligibility.engine import evaluate_eligibility
from app.models.rag import GuidelineChunk, GuidelineDocument
from app.models.scholarship import Scholarship, ScholarshipVersion
from app.models.tracking import SavedScholarship
from app.models.user import StudentProfile
from app.schemas.eligibility import CriterionEvaluationSchema, EligibilityEvaluationSchema
from app.schemas.scholarship import (
    EvidenceSnippetSchema,
    ScholarshipCreateUpdate,
    ScholarshipDetail,
    ScholarshipListItem,
    ScholarshipListResponse,
    ScholarshipVersionSchema,
)
from app.services.notification_service import profile_to_dict


def _to_eligibility_schema(ev) -> EligibilityEvaluationSchema:
    return EligibilityEvaluationSchema(
        overall_status=ev.overall_status,
        overall_label=ev.overall_label,
        summary=ev.summary,
        criteria_results=[
            CriterionEvaluationSchema(
                key=c.key,
                criterion_name=c.criterion_name,
                rule_description=c.rule_description,
                result=c.result,
                mandatory=c.mandatory,
                profile_value_display=c.profile_value_display,
                explanation=c.explanation,
                source_reference=c.source_reference,
            )
            for c in ev.criteria_results
        ],
        passed_count=ev.passed_count,
        failed_count=ev.failed_count,
        unknown_count=ev.unknown_count,
        missing_fields=ev.missing_fields,
        disclaimer=ev.disclaimer,
    )


def list_scholarships_for_user(
    db: Session,
    *,
    profile: StudentProfile | None,
    saved_ids: set[str],
    q: str | None = None,
    study_scope: str | None = None,
    destination_country: str | None = None,
    funding_type: str | None = None,
    university: str | None = None,
    education_level: str | None = None,
    state_ut: str | None = None,
    scholarship_type: str | None = None,
    status: str | None = None,
    provider: str | None = None,
    sort: str = "relevance",
    page: int = 1,
    page_size: int = 12,
    include_inactive: bool = False,
) -> ScholarshipListResponse:
    stmt = select(Scholarship)
    if not include_inactive:
        stmt = stmt.where(Scholarship.is_active.is_(True))

    if q and q.strip():
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                Scholarship.name.ilike(like),
                Scholarship.provider.ilike(like),
                Scholarship.description.ilike(like),
            )
        )
    if study_scope and study_scope.strip():
        stmt = stmt.where(Scholarship.study_scope == study_scope.strip())
    if funding_type and funding_type.strip():
        stmt = stmt.where(Scholarship.funding_type == funding_type.strip())
    if scholarship_type and scholarship_type.strip():
        stmt = stmt.where(Scholarship.scholarship_type == scholarship_type.strip())
    if status and status.strip():
        stmt = stmt.where(Scholarship.status == status.strip().upper())
    if provider and provider.strip():
        stmt = stmt.where(Scholarship.provider.ilike(f"%{provider.strip()}%"))

    all_active = list(db.scalars(select(Scholarship).where(Scholarship.is_active.is_(True))).all())
    available_filters = {
        "study_scopes": sorted({s.study_scope for s in all_active}),
        "destination_countries": sorted(
            {c for s in all_active for c in (s.destination_countries or [])}
        ),
        "funding_types": sorted({s.funding_type for s in all_active}),
        "education_levels": sorted(
            {lv for s in all_active for lv in (s.education_levels or [])}
        ),
        "states": sorted(
            {st for s in all_active for st in (s.applicable_states or [])}
        ),
        "scholarship_types": sorted({s.scholarship_type for s in all_active}),
        "statuses": sorted({s.status for s in all_active}),
        "providers": sorted({s.provider for s in all_active}),
    }

    rows = list(db.scalars(stmt).all())
    profile_dict = profile_to_dict(profile)
    filtered_items: list[tuple[Scholarship, EligibilityEvaluationSchema | None, int]] = []

    for s in rows:
        if education_level and education_level.strip():
            levels = [lv.lower() for lv in (s.education_levels or [])]
            if education_level.strip().lower() not in levels:
                continue
        if state_ut and state_ut.strip():
            states = [st.lower() for st in (s.applicable_states or [])]
            if "all india" not in states and state_ut.strip().lower() not in states:
                continue
        if destination_country and destination_country.strip():
            dests = [d.lower() for d in (s.destination_countries or [])]
            if destination_country.strip().lower() not in dests:
                continue
        if university and university.strip():
            uni_q = university.strip().lower()
            unis = [u.lower() for u in (s.target_universities or [])]
            if unis and not any(uni_q in u or "accredited" in u or "any" in u for u in unis):
                if uni_q not in (s.institution_constraints or "").lower():
                    continue

        ev_schema: EligibilityEvaluationSchema | None = None
        relevance_rank = 2
        if profile is not None:
            ev = evaluate_eligibility(s.structured_rules, profile_dict)
            ev_schema = _to_eligibility_schema(ev)
            if ev.overall_status == "POTENTIAL_MATCH":
                relevance_rank = 0
            elif ev.overall_status == "NEEDS_MORE_INFORMATION":
                relevance_rank = 1
            else:
                relevance_rank = 3
            # Boost matches aligning with student's preferred destination countries or funding types
            pref_dests = {d.lower() for d in (profile.preferred_destination_countries or [])}
            if pref_dests and relevance_rank <= 1:
                schol_dests = {d.lower() for d in (s.destination_countries or [])}
                if pref_dests & schol_dests:
                    relevance_rank = max(0, relevance_rank)
        filtered_items.append((s, ev_schema, relevance_rank))

    if sort == "deadline":
        filtered_items.sort(
            key=lambda x: (
                x[0].application_deadline is None,
                x[0].application_deadline or datetime.max.date(),
                x[2],
            )
        )
    elif sort == "recently_verified":
        filtered_items.sort(
            key=lambda x: (
                x[0].last_verified_at is None,
                -(x[0].last_verified_at.timestamp() if x[0].last_verified_at else 0.0),
            )
        )
    else:
        filtered_items.sort(
            key=lambda x: (
                x[2],
                0 if x[0].status == "OPEN" else (1 if x[0].status == "UPCOMING" else 2),
                x[0].application_deadline is None,
                x[0].application_deadline or datetime.max.date(),
            )
        )

    total = len(filtered_items)
    total_pages = max(1, ceil(total / page_size)) if total else 1
    safe_page = max(1, min(page, total_pages))
    start = (safe_page - 1) * page_size
    page_slice = filtered_items[start : start + page_size]

    items: list[ScholarshipListItem] = []
    for s, ev_schema, _ in page_slice:
        match_reason = ev_schema.summary if ev_schema else s.status_reason
        items.append(
            ScholarshipListItem(
                id=s.id,
                slug=s.slug,
                name=s.name,
                provider=s.provider,
                provider_type=s.provider_type,
                scholarship_type=s.scholarship_type,
                description=s.description,
                study_scope=s.study_scope,
                destination_countries=s.destination_countries or [],
                target_universities=s.target_universities or [],
                eligible_nationalities=s.eligible_nationalities or [],
                funding_type=s.funding_type,
                applicable_states=s.applicable_states or [],
                education_levels=s.education_levels or [],
                courses=s.courses or [],
                benefit_amount_display=s.benefit_amount_display,
                benefit_amount_inr=s.benefit_amount_inr,
                benefit_type=s.benefit_type,
                application_start_date=s.application_start_date,
                application_deadline=s.application_deadline,
                deadline_timezone=s.deadline_timezone,
                status=s.status,
                status_reason=s.status_reason,
                official_info_url=s.official_info_url,
                official_application_url=s.official_application_url,
                source_type=s.source_type,
                source_url=s.source_url,
                last_checked_at=s.last_checked_at,
                last_verified_at=s.last_verified_at,
                verification_state=s.verification_state,
                current_version=s.current_version,
                eligibility=ev_schema,
                match_reason=match_reason,
                is_saved=s.id in saved_ids,
            )
        )

    return ScholarshipListResponse(
        items=items,
        total=total,
        page=safe_page,
        page_size=page_size,
        total_pages=total_pages,
        available_filters=available_filters,
    )


def get_scholarship_detail(
    db: Session,
    scholarship_id_or_slug: str,
    *,
    profile: StudentProfile | None,
    saved_ids: set[str],
) -> ScholarshipDetail | None:
    s = db.scalar(
        select(Scholarship).where(
            or_(
                Scholarship.id == scholarship_id_or_slug,
                Scholarship.slug == scholarship_id_or_slug,
            )
        )
    )
    if not s:
        return None

    ev_schema = (
        _to_eligibility_schema(evaluate_eligibility(s.structured_rules, profile_to_dict(profile)))
        if profile is not None
        else None
    )

    chunk_rows = list(
        db.execute(
            select(GuidelineChunk, GuidelineDocument.title)
            .join(GuidelineDocument, GuidelineChunk.document_id == GuidelineDocument.id)
            .where(GuidelineChunk.scholarship_id == s.id)
            .order_by(GuidelineChunk.chunk_index.asc())
            .limit(6)
        ).all()
    )
    evidence = [
        EvidenceSnippetSchema(
            chunk_id=ch.id,
            document_title=doc_title,
            source_url=ch.source_url,
            page_number=ch.page_number,
            section_heading=ch.section_heading,
            verification_status=ch.verification_status,
            retrieved_at=ch.retrieved_at,
            excerpt=ch.content[:500],
        )
        for ch, doc_title in chunk_rows
    ]

    versions = list(
        db.scalars(
            select(ScholarshipVersion)
            .where(ScholarshipVersion.scholarship_id == s.id)
            .order_by(ScholarshipVersion.version_number.desc())
            .limit(10)
        ).all()
    )

    return ScholarshipDetail(
        id=s.id,
        slug=s.slug,
        name=s.name,
        provider=s.provider,
        provider_type=s.provider_type,
        scholarship_type=s.scholarship_type,
        description=s.description,
        study_scope=s.study_scope,
        destination_countries=s.destination_countries or [],
        target_universities=s.target_universities or [],
        eligible_nationalities=s.eligible_nationalities or [],
        funding_type=s.funding_type,
        applicable_states=s.applicable_states or [],
        education_levels=s.education_levels or [],
        courses=s.courses or [],
        institution_constraints=s.institution_constraints,
        benefit_amount_display=s.benefit_amount_display,
        benefit_amount_inr=s.benefit_amount_inr,
        benefit_type=s.benefit_type,
        structured_rules=s.structured_rules or {},
        required_documents=s.required_documents or [],
        application_steps=s.application_steps or [],
        application_start_date=s.application_start_date,
        application_deadline=s.application_deadline,
        deadline_timezone=s.deadline_timezone,
        status=s.status,
        status_reason=s.status_reason,
        official_info_url=s.official_info_url,
        official_application_url=s.official_application_url,
        source_type=s.source_type,
        source_url=s.source_url,
        source_publication_date=s.source_publication_date,
        last_checked_at=s.last_checked_at,
        last_verified_at=s.last_verified_at,
        verification_state=s.verification_state,
        current_version=s.current_version,
        eligibility=ev_schema,
        match_reason=ev_schema.summary if ev_schema else s.status_reason,
        is_saved=s.id in saved_ids,
        evidence_snippets=evidence,
        recent_versions=[ScholarshipVersionSchema.model_validate(v) for v in versions],
    )


def create_or_update_scholarship_admin(
    db: Session,
    *,
    payload: ScholarshipCreateUpdate,
    admin_email: str,
    scholarship: Scholarship | None = None,
) -> Scholarship:
    now = datetime.now(UTC)
    data = payload.model_dump()
    data["structured_rules"] = payload.structured_rules.model_dump()
    data["required_documents"] = [item.model_dump() for item in payload.required_documents]

    if scholarship is None:
        s = Scholarship(
            **data,
            last_checked_at=now,
            last_verified_at=now if payload.verification_state == "VERIFIED" else None,
            current_version=1,
        )
        db.add(s)
        db.flush()
        db.add(
            ScholarshipVersion(
                scholarship_id=s.id,
                version_number=1,
                snapshot=data,
                changed_fields={"created": {"old": None, "new": "Created by admin"}},
                change_source=f"admin:{admin_email}",
                source_url=s.source_url,
                reviewed=True,
                reviewed_by=admin_email,
                reviewed_at=now,
            )
        )
        db.commit()
        db.refresh(s)
        return s

    old_snapshot = {
        "name": scholarship.name,
        "status": scholarship.status,
        "application_deadline": scholarship.application_deadline.isoformat()
        if scholarship.application_deadline
        else None,
        "benefit_amount_display": scholarship.benefit_amount_display,
        "structured_rules": scholarship.structured_rules,
    }
    changed: dict = {}
    for k, new_val in data.items():
        old_val = getattr(scholarship, k)
        if old_val != new_val:
            changed[k] = {
                "old": old_val.isoformat() if hasattr(old_val, "isoformat") else old_val,
                "new": new_val.isoformat() if hasattr(new_val, "isoformat") else new_val,
            }
            setattr(scholarship, k, new_val)

    scholarship.last_checked_at = now
    if payload.verification_state == "VERIFIED":
        scholarship.last_verified_at = now
    if changed:
        scholarship.current_version += 1
        db.add(
            ScholarshipVersion(
                scholarship_id=scholarship.id,
                version_number=scholarship.current_version,
                snapshot=old_snapshot,
                changed_fields=changed,
                change_source=f"admin:{admin_email}",
                source_url=scholarship.source_url,
                reviewed=True,
                reviewed_by=admin_email,
                reviewed_at=now,
            )
        )
    db.add(scholarship)
    db.commit()
    db.refresh(scholarship)
    return scholarship


def get_user_saved_ids(db: Session, user_id: str) -> set[str]:
    return set(
        db.scalars(
            select(SavedScholarship.scholarship_id).where(SavedScholarship.user_id == user_id)
        ).all()
    )
