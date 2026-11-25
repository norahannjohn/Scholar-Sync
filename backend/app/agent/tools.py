from __future__ import annotations

from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.agent.web_discovery import (
    discover_and_verify_official_sites,
    fetch_and_verify_official_url,
)
from app.eligibility.engine import evaluate_eligibility
from app.models.scholarship import Scholarship, ScholarshipSource
from app.models.tracking import SavedScholarship, StudentApplication
from app.models.user import StudentProfile, User
from app.rag.retriever import retrieve_passages
from app.schemas.assistant import (
    ChecklistItemSchema,
    ChecklistResponse,
    CitationSchema,
    LiveVerificationResult,
)
from app.services.notification_service import profile_to_dict


class ControlledAgentTools:
    """Explicit backend + live official-website discovery tools scoped to current_user."""

    def __init__(self, db: Session, user: User) -> None:
        self.db = db
        self.user = user
        self.profile: StudentProfile | None = db.scalar(
            select(StudentProfile).where(StudentProfile.user_id == user.id)
        )
        self.collected_citations: list[CitationSchema] = []
        self.live_verifications: list[LiveVerificationResult] = []
        self.tool_calls_used: list[str] = []

    def _record_tool(self, name: str) -> None:
        if name not in self.tool_calls_used:
            self.tool_calls_used.append(name)

    def search_scholarships(
        self,
        query: str = "",
        study_scope: str = "",
        destination_country: str = "",
        funding_type: str = "",
        university: str = "",
        education_level: str = "",
        state_ut: str = "",
        status: str = "",
    ) -> dict[str, Any]:
        """Search ScholarSync's catalogue across India & international schemes and evaluate eligibility."""
        self._record_tool("search_scholarships")
        stmt = select(Scholarship).where(Scholarship.is_active.is_(True))
        if query.strip():
            like = f"%{query.strip()}%"
            stmt = stmt.where(
                or_(
                    Scholarship.name.ilike(like),
                    Scholarship.provider.ilike(like),
                    Scholarship.description.ilike(like),
                )
            )
        if study_scope.strip():
            stmt = stmt.where(Scholarship.study_scope == study_scope.strip())
        if funding_type.strip():
            stmt = stmt.where(Scholarship.funding_type == funding_type.strip())
        if status.strip():
            stmt = stmt.where(Scholarship.status == status.strip().upper())

        rows = list(
            self.db.scalars(
                stmt.order_by(Scholarship.application_deadline.asc().nulls_last())
            ).all()
        )
        profile_dict = profile_to_dict(self.profile)
        results: list[dict[str, Any]] = []

        for s in rows:
            if education_level.strip():
                levels = [lv.lower() for lv in (s.education_levels or [])]
                if education_level.strip().lower() not in levels:
                    continue
            if destination_country.strip():
                dests = [d.lower() for d in (s.destination_countries or [])]
                if not any(destination_country.strip().lower() in d for d in dests):
                    continue
            if university.strip():
                uni_q = university.strip().lower()
                unis = [u.lower() for u in (s.target_universities or [])]
                if unis and not any(uni_q in u or "accredited" in u or "any" in u for u in unis):
                    if uni_q not in (s.institution_constraints or "").lower():
                        continue
            if state_ut.strip():
                states = [st.lower() for st in (s.applicable_states or [])]
                if "all india" not in states and state_ut.strip().lower() not in states:
                    continue

            ev = evaluate_eligibility(s.structured_rules, profile_dict)
            results.append(
                {
                    "scholarship_id": s.id,
                    "slug": s.slug,
                    "name": s.name,
                    "provider": s.provider,
                    "study_scope": s.study_scope,
                    "destination_countries": s.destination_countries,
                    "target_universities": s.target_universities,
                    "eligible_nationalities": s.eligible_nationalities,
                    "funding_type": s.funding_type,
                    "status": s.status,
                    "application_deadline": s.application_deadline.isoformat()
                    if s.application_deadline
                    else None,
                    "benefit_amount_display": s.benefit_amount_display,
                    "verification_state": s.verification_state,
                    "official_info_url": s.official_info_url,
                    "official_application_url": s.official_application_url,
                    "eligibility_overall_status": ev.overall_status,
                    "eligibility_label": ev.overall_label,
                    "eligibility_summary": ev.summary,
                    "missing_fields": ev.missing_fields,
                }
            )

        eligible_or_pending = [
            r for r in results if r["eligibility_overall_status"] != "NOT_ELIGIBLE"
        ]
        ruled_out = [r for r in results if r["eligibility_overall_status"] == "NOT_ELIGIBLE"]
        return {
            "total_matching_query": len(results),
            "potential_or_needs_info": eligible_or_pending[:10],
            "not_eligible": ruled_out[:5],
        }

    def discover_and_verify_official_web(
        self,
        query: str,
        destination_country: str = "",
        education_level: str = "",
        study_scope: str = "",
    ) -> dict[str, Any]:
        """Actively search and live-verify official scholarship websites and PDFs right now."""
        self._record_tool("discover_and_verify_official_web")
        res = discover_and_verify_official_sites(
            self.db,
            query=query,
            destination_country=destination_country,
            education_level=education_level,
            study_scope=study_scope,
        )
        for item in res.get("verified_results", []) + res.get("unreachable_results", []):
            lv = LiveVerificationResult(
                title=item["title"],
                url=item["url"],
                http_status=item.get("http_status"),
                verified_live=item["verified_live"],
                checked_at=item["checked_at"],
                excerpt=item.get("excerpt"),
                discovered_links=item.get("discovered_links", []),
                error=item.get("error"),
            )
            if not any(existing.url == lv.url for existing in self.live_verifications):
                self.live_verifications.append(lv)
            if item["verified_live"] and item.get("excerpt"):
                cit = CitationSchema(
                    title=f"[Live Check] {item['title']}",
                    source_url=item["url"],
                    page_number=None,
                    section_heading="Live Official Website Verification",
                    verification_status="LIVE_VERIFIED",
                    excerpt=item["excerpt"][:500],
                )
                if not any(c.source_url == cit.source_url for c in self.collected_citations):
                    self.collected_citations.append(cit)
        return res

    def verify_official_url(self, url: str, question: str = "") -> dict[str, Any]:
        """Live-fetch and verify a specific official scholarship URL or PDF guideline."""
        self._record_tool("verify_official_url")
        registered = list(
            self.db.scalars(select(ScholarshipSource).where(ScholarshipSource.is_active.is_(True))).all()
        )
        registered_hosts = {
            urlparse(s.url).hostname.lower() for s in registered if urlparse(s.url).hostname
        }
        item = fetch_and_verify_official_url(
            url, query=question, registered_hosts=registered_hosts
        )
        lv = LiveVerificationResult(
            title=item["title"],
            url=item["url"],
            http_status=item.get("http_status"),
            verified_live=item["verified_live"],
            checked_at=item["checked_at"],
            excerpt=item.get("excerpt"),
            discovered_links=item.get("discovered_links", []),
            error=item.get("error"),
        )
        if not any(existing.url == lv.url for existing in self.live_verifications):
            self.live_verifications.append(lv)
        if item["verified_live"] and item.get("excerpt"):
            cit = CitationSchema(
                title=f"[Live Check] {item['title']}",
                source_url=item["url"],
                page_number=None,
                section_heading="Live Official Page / PDF",
                verification_status="LIVE_VERIFIED",
                excerpt=item["excerpt"][:500],
            )
            if not any(c.source_url == cit.source_url for c in self.collected_citations):
                self.collected_citations.append(cit)
        return item

    def get_scholarship_details(self, scholarship_id: str) -> dict[str, Any]:
        """Return full stored scholarship record, destination, funding, deadlines, and freshness."""
        self._record_tool("get_scholarship_details")
        s = self.db.scalar(
            select(Scholarship).where(
                or_(Scholarship.id == scholarship_id, Scholarship.slug == scholarship_id)
            )
        )
        if not s:
            return {"error": f"Scholarship '{scholarship_id}' was not found in the database."}
        return {
            "scholarship_id": s.id,
            "slug": s.slug,
            "name": s.name,
            "provider": s.provider,
            "provider_type": s.provider_type,
            "scholarship_type": s.scholarship_type,
            "study_scope": s.study_scope,
            "destination_countries": s.destination_countries,
            "target_universities": s.target_universities,
            "eligible_nationalities": s.eligible_nationalities,
            "funding_type": s.funding_type,
            "description": s.description,
            "applicable_states": s.applicable_states,
            "education_levels": s.education_levels,
            "courses": s.courses,
            "institution_constraints": s.institution_constraints,
            "benefit_amount_display": s.benefit_amount_display,
            "application_start_date": s.application_start_date.isoformat()
            if s.application_start_date
            else None,
            "application_deadline": s.application_deadline.isoformat()
            if s.application_deadline
            else None,
            "deadline_timezone": s.deadline_timezone,
            "status": s.status,
            "status_reason": s.status_reason,
            "official_info_url": s.official_info_url,
            "official_application_url": s.official_application_url,
            "source_url": s.source_url,
            "verification_state": s.verification_state,
            "last_checked_at": s.last_checked_at.isoformat() if s.last_checked_at else None,
            "last_verified_at": s.last_verified_at.isoformat() if s.last_verified_at else None,
        }

    def evaluate_eligibility_for_student(self, scholarship_id: str) -> dict[str, Any]:
        """Run the deterministic Python rules engine for the authenticated student."""
        self._record_tool("evaluate_eligibility")
        s = self.db.scalar(
            select(Scholarship).where(
                or_(Scholarship.id == scholarship_id, Scholarship.slug == scholarship_id)
            )
        )
        if not s:
            return {"error": f"Scholarship '{scholarship_id}' was not found."}
        ev = evaluate_eligibility(s.structured_rules, profile_to_dict(self.profile))
        return {
            "scholarship_id": s.id,
            "scholarship_name": s.name,
            "overall_status": ev.overall_status,
            "overall_label": ev.overall_label,
            "summary": ev.summary,
            "missing_fields": ev.missing_fields,
            "criteria": [
                {
                    "criterion_name": c.criterion_name,
                    "rule_description": c.rule_description,
                    "result": c.result,
                    "mandatory": c.mandatory,
                    "profile_value_display": c.profile_value_display,
                    "explanation": c.explanation,
                    "source_reference": c.source_reference,
                }
                for c in ev.criteria_results
            ],
            "disclaimer": ev.disclaimer,
        }

    def retrieve_guideline_evidence(self, scholarship_id: str, question: str) -> dict[str, Any]:
        """Retrieve relevant official guideline passages with source metadata and page numbers."""
        self._record_tool("retrieve_guideline_evidence")
        s = self.db.scalar(
            select(Scholarship).where(
                or_(Scholarship.id == scholarship_id, Scholarship.slug == scholarship_id)
            )
        )
        target_id = s.id if s else None
        passages = retrieve_passages(self.db, question, scholarship_id=target_id, limit=4)
        out = []
        for p in passages:
            citation = CitationSchema(
                title=p.document_title,
                source_url=p.source_url,
                page_number=p.page_number,
                section_heading=p.section_heading,
                verification_status=p.verification_status,
                excerpt=p.excerpt,
            )
            if not any(
                c.source_url == citation.source_url and c.excerpt == citation.excerpt
                for c in self.collected_citations
            ):
                self.collected_citations.append(citation)
            out.append(citation.model_dump())
        return {
            "passages_found": len(out),
            "passages": out,
        }

    def get_application_checklist(self, scholarship_id: str) -> dict[str, Any]:
        """Assemble a source-linked document checklist and walkthrough for a scholarship."""
        self._record_tool("get_application_checklist")
        s = self.db.scalar(
            select(Scholarship).where(
                or_(Scholarship.id == scholarship_id, Scholarship.slug == scholarship_id)
            )
        )
        if not s:
            return {"error": f"Scholarship '{scholarship_id}' was not found."}
        checklist = build_checklist_response(s)
        return checklist.model_dump()

    def save_scholarship(self, scholarship_id: str) -> dict[str, Any]:
        """Save a scholarship to the authenticated student's saved list."""
        self._record_tool("save_scholarship")
        s = self.db.scalar(
            select(Scholarship).where(
                or_(Scholarship.id == scholarship_id, Scholarship.slug == scholarship_id)
            )
        )
        if not s:
            return {"error": f"Scholarship '{scholarship_id}' was not found."}
        existing = self.db.scalar(
            select(SavedScholarship).where(
                SavedScholarship.user_id == self.user.id,
                SavedScholarship.scholarship_id == s.id,
            )
        )
        if not existing:
            self.db.add(SavedScholarship(user_id=self.user.id, scholarship_id=s.id))
            self.db.commit()
        return {"saved": True, "scholarship_id": s.id, "scholarship_name": s.name}

    def update_tracking_status(
        self, scholarship_id: str, status: str, notes: str = ""
    ) -> dict[str, Any]:
        """Update the authenticated user's self-maintained application progress status."""
        self._record_tool("update_tracking_status")
        allowed = {
            "INTERESTED",
            "PREPARING",
            "READY_TO_APPLY",
            "SUBMITTED",
            "AWAITING_UPDATE",
            "AWARDED",
            "NOT_SELECTED",
        }
        norm_status = status.strip().upper()
        if norm_status not in allowed:
            return {"error": f"Unsupported tracking status '{status}'. Allowed: {sorted(allowed)}"}
        s = self.db.scalar(
            select(Scholarship).where(
                or_(Scholarship.id == scholarship_id, Scholarship.slug == scholarship_id)
            )
        )
        if not s:
            return {"error": f"Scholarship '{scholarship_id}' was not found."}
        app_row = self.db.scalar(
            select(StudentApplication).where(
                StudentApplication.user_id == self.user.id,
                StudentApplication.scholarship_id == s.id,
            )
        )
        if app_row:
            app_row.status = norm_status
            if notes.strip():
                app_row.notes = notes.strip()
        else:
            app_row = StudentApplication(
                user_id=self.user.id,
                scholarship_id=s.id,
                status=norm_status,
                notes=notes.strip() or None,
            )
        self.db.add(app_row)
        self.db.commit()
        return {
            "updated": True,
            "scholarship_id": s.id,
            "scholarship_name": s.name,
            "status": norm_status,
            "note": "User-maintained tracking status updated (this does not submit to any official portal).",
        }


def build_checklist_response(scholarship: Scholarship) -> ChecklistResponse:
    items: list[ChecklistItemSchema] = []
    for raw in scholarship.required_documents or []:
        if isinstance(raw, dict) and raw.get("item"):
            req_level = raw.get("status", "confirm_with_provider")
            if req_level not in ("required", "conditional", "confirm_with_provider"):
                req_level = "confirm_with_provider"
            items.append(
                ChecklistItemSchema(
                    item=str(raw["item"]),
                    requirement_level=req_level,
                    note=raw.get("note"),
                    source_url=scholarship.source_url,
                )
            )

    if not items:
        items.append(
            ChecklistItemSchema(
                item="Confirm full required document list on the official provider portal",
                requirement_level="confirm_with_provider",
                note="No structured document list was extracted from the official guideline yet.",
                source_url=scholarship.official_info_url,
            )
        )

    steps = list(scholarship.application_steps or [])
    if not steps:
        steps = [
            f"Read the official scholarship guideline at {scholarship.official_info_url}.",
            "Confirm your eligibility and prepare supporting academic/income/category documents.",
            (
                f"Submit your application on the official portal: {scholarship.official_application_url}."
                if scholarship.official_application_url
                else "Follow the official submission instructions published by the provider."
            ),
        ]

    checked_str = (
        scholarship.last_checked_at.strftime("%Y-%m-%d %H:%M UTC")
        if isinstance(scholarship.last_checked_at, datetime)
        else "unknown"
    )
    return ChecklistResponse(
        scholarship_id=scholarship.id,
        scholarship_name=scholarship.name,
        official_info_url=scholarship.official_info_url,
        official_application_url=scholarship.official_application_url,
        verification_state=scholarship.verification_state,
        items=items,
        application_steps=steps,
        disclaimer=(
            f"Source verification state: {scholarship.verification_state} (last checked {checked_str}). "
            "Confirm exact document formats and deadlines on the official provider portal before applying."
        ),
    )
