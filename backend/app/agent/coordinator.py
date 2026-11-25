from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.agent.fallback import build_fallback_assistant_reply
from app.agent.tools import ControlledAgentTools
from app.core.config import get_settings
from app.models.user import User
from app.schemas.assistant import AssistantChatResponse

logger = logging.getLogger(__name__)

SYSTEM_INSTRUCTION = """You are ScholarSync's Scholarship-Discovery & Eligibility Agent for students in India — covering BOTH scholarships within India AND international scholarships open to Indian applicants for studying abroad.

You are NOT a government officer, university admissions office, or scholarship provider.

Strict agent workflow & rules:
1. When a student describes their goals in natural language (country, university, course, degree level, funding type, nationality, or personal background), you MUST:
   a) Search ScholarSync's catalogue using `search_scholarships` (with `study_scope`, `destination_country`, `funding_type`, `university`, `education_level`, `query`), AND
   b) Actively search and live-verify relevant official scholarship websites using `discover_and_verify_official_web` (and `verify_official_url` for specific official scheme pages or guideline PDFs you want to inspect).
   c) Evaluate deterministic eligibility using `evaluate_eligibility_for_student` and retrieve RAG passages via `retrieve_guideline_evidence` where catalogue records exist.
2. NEVER invent deadlines, award amounts, university lists, nationality rules, eligibility criteria, URLs, or page numbers. Only state facts directly returned by tools or live-verified official pages.
3. If an official website is unreachable, timed out, or lacks a specific detail (e.g., next cycle deadline), state that gap clearly and give the official URL so the student can check directly.
4. Eligibility is decided exclusively by the deterministic Python rules engine. NEVER override `NOT_ELIGIBLE` (`FAIL`) or guarantee selection.
5. Distinguish clearly: `Potential match`, `More information needed` (name the missing profile fields), and `Not eligible based on the information entered`.
6. Cover international factors clearly when relevant: destination country, eligible host universities, nationality requirements, funding type (full funding vs tuition vs stipend), and language/work-experience prerequisites.
7. NEVER ask for Aadhaar numbers, bank account details, portal passwords, or certificate uploads.
8. NEVER claim to have submitted an application, verified a certificate, or contacted a provider.
9. Only call `save_scholarship` or `update_tracking_status` when the student explicitly asks to save or update their personal tracker."""


def run_assistant_turn(
    db: Session,
    user: User,
    message: str,
    scholarship_id: str | None = None,
) -> AssistantChatResponse:
    settings = get_settings()
    if not settings.gemini_configured:
        return build_fallback_assistant_reply(
            db, user, message, scholarship_id, mode="fallback_no_key"
        )

    tools = ControlledAgentTools(db, user)

    def search_scholarships(
        query: str = "",
        study_scope: str = "",
        destination_country: str = "",
        funding_type: str = "",
        university: str = "",
        education_level: str = "",
        state_ut: str = "",
        status: str = "",
    ) -> dict[str, Any]:
        """Search ScholarSync's domestic India and international scholarship catalogue and run deterministic eligibility checks."""
        return tools.search_scholarships(
            query=query,
            study_scope=study_scope,
            destination_country=destination_country,
            funding_type=funding_type,
            university=university,
            education_level=education_level,
            state_ut=state_ut,
            status=status,
        )

    def discover_and_verify_official_web(
        query: str,
        destination_country: str = "",
        education_level: str = "",
        study_scope: str = "",
    ) -> dict[str, Any]:
        """Actively search and live-verify official scholarship websites and PDFs for the student's query."""
        return tools.discover_and_verify_official_web(
            query=query,
            destination_country=destination_country,
            education_level=education_level,
            study_scope=study_scope,
        )

    def verify_official_url(url: str, question: str = "") -> dict[str, Any]:
        """Live-fetch and verify a specific official scholarship URL or guideline PDF."""
        return tools.verify_official_url(url=url, question=question)

    def get_scholarship_details(scholarship_id: str) -> dict[str, Any]:
        """Get stored scholarship details, destination countries, funding type, dates, and source freshness."""
        return tools.get_scholarship_details(scholarship_id)

    def evaluate_eligibility_for_student(scholarship_id: str) -> dict[str, Any]:
        """Run the deterministic Python eligibility rules engine for a specific scholarship."""
        return tools.evaluate_eligibility_for_student(scholarship_id)

    def retrieve_guideline_evidence(scholarship_id: str, question: str) -> dict[str, Any]:
        """Retrieve relevant official guideline passages with source URL and page numbers."""
        return tools.retrieve_guideline_evidence(scholarship_id, question)

    def get_application_checklist(scholarship_id: str) -> dict[str, Any]:
        """Assemble the official document checklist and numbered application walkthrough."""
        return tools.get_application_checklist(scholarship_id)

    def save_scholarship(scholarship_id: str) -> dict[str, Any]:
        """Save a scholarship to the student's saved list when the user explicitly asks to save it."""
        return tools.save_scholarship(scholarship_id)

    def update_tracking_status(scholarship_id: str, status: str, notes: str = "") -> dict[str, Any]:
        """Update the student's self-maintained application progress status when explicitly requested."""
        return tools.update_tracking_status(scholarship_id, status, notes)

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=settings.gemini_api_key.strip())
        prompt_text = message
        if scholarship_id:
            prompt_text = (
                f"[Context: the student is currently viewing scholarship_id='{scholarship_id}']\n\n"
                f"{message}"
            )

        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt_text,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                tools=[
                    search_scholarships,
                    discover_and_verify_official_web,
                    verify_official_url,
                    get_scholarship_details,
                    evaluate_eligibility_for_student,
                    retrieve_guideline_evidence,
                    get_application_checklist,
                    save_scholarship,
                    update_tracking_status,
                ],
                temperature=0.2,
            ),
        )
        reply_text = (response.text or "").strip()
        if not reply_text:
            return build_fallback_assistant_reply(
                db,
                user,
                message,
                scholarship_id,
                mode="fallback_error",
                error_reason="Empty response from Gemini",
            )
        return AssistantChatResponse(
            reply=reply_text,
            mode="gemini",
            citations=tools.collected_citations,
            live_verifications=tools.live_verifications,
            tool_calls_used=tools.tool_calls_used,
            gemini_configured=True,
            disclaimer=(
                "AI explanations combine deterministic rule outputs, stored official records, and live "
                "official website checks. Verify final details and apply directly on the official portal."
            ),
        )
    except Exception as exc:
        logger.warning(
            "Gemini assistant call failed; falling back to deterministic mode: %s",
            type(exc).__name__,
        )
        return build_fallback_assistant_reply(
            db,
            user,
            message,
            scholarship_id,
            mode="fallback_error",
            error_reason=type(exc).__name__,
        )
