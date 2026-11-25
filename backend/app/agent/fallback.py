from __future__ import annotations

from sqlalchemy.orm import Session

from app.agent.tools import ControlledAgentTools
from app.agent.web_discovery import extract_query_intent
from app.models.user import User
from app.schemas.assistant import AssistantChatResponse


def build_fallback_assistant_reply(
    db: Session,
    user: User,
    message: str,
    scholarship_id: str | None = None,
    *,
    mode: str = "fallback_no_key",
    error_reason: str | None = None,
) -> AssistantChatResponse:
    """Deterministic + live official-website discovery fallback when Gemini key is absent or unavailable."""
    tools = ControlledAgentTools(db, user)
    lines: list[str] = []

    if mode == "fallback_no_key":
        lines.append(
            "**Conversational Gemini AI is not configured yet** (`GEMINI_API_KEY` not set). "
            "Running ScholarSync's deterministic rules engine, catalogue search, and live official-website verification:"
        )
    else:
        lines.append(
            "**Conversational Gemini AI is temporarily unavailable**"
            + (f" ({error_reason})" if error_reason else "")
            + ". Showing deterministic eligibility results and live official-source verification:"
        )

    if scholarship_id:
        ev = tools.evaluate_eligibility_for_student(scholarship_id)
        details = tools.get_scholarship_details(scholarship_id)
        if "error" not in ev and "error" not in details:
            lines.append("")
            lines.append(f"### {details['name']}")
            lines.append(
                f"- **Study Scope & Destination:** {details['study_scope']} • "
                f"{', '.join(details.get('destination_countries') or [])}"
            )
            lines.append(
                f"- **Funding Type:** {details.get('funding_type', '').replace('_', ' ')} "
                + (
                    f"({details['benefit_amount_display']})"
                    if details.get("benefit_amount_display")
                    else ""
                )
            )
            lines.append(
                f"- **Preliminary Eligibility:** {ev['overall_label']} — {ev['summary']}"
            )
            lines.append(
                f"- **Official Status & Deadline:** {details['status']} "
                + (
                    f"(Deadline: {details['application_deadline']} {details['deadline_timezone']})"
                    if details.get("application_deadline")
                    else "(No fixed closing date recorded)"
                )
            )
            if ev.get("missing_fields"):
                lines.append(
                    "- **Missing Profile Details Needed:** "
                    + ", ".join(f.replace("_", " ") for f in ev["missing_fields"])
                )
            lines.append(f"- **Official Info:** {details['official_info_url']}")
            if details.get("official_application_url"):
                lines.append(f"- **Official Portal:** {details['official_application_url']}")

            checklist = tools.get_application_checklist(scholarship_id)
            if checklist.get("items"):
                lines.append("")
                lines.append("**Document Checklist:**")
                for item in checklist["items"][:6]:
                    lines.append(
                        f"- [{item['requirement_level']}] {item['item']}"
                        + (f" — {item['note']}" if item.get("note") else "")
                    )

            tools.retrieve_guideline_evidence(scholarship_id, message)
            tools.verify_official_url(details["official_info_url"], question=message)
    else:
        intent = extract_query_intent(message)
        dest_country = (
            intent["destination_countries"][0] if intent["destination_countries"] else ""
        )
        search_res = tools.search_scholarships(
            query="",
            study_scope=intent["study_scope"],
            destination_country=dest_country,
            funding_type=intent["funding_type"],
            education_level=intent["education_level"],
        )
        # If filtered search returns empty (e.g. student mentioned a niche country or keyword), broaden catalogue search
        if search_res["total_matching_query"] == 0:
            search_res = tools.search_scholarships(query="")

        candidates = search_res.get("potential_or_needs_info", [])
        ruled_out = search_res.get("not_eligible", [])
        lines.append("")
        if candidates:
            lines.append("**Matching Scholarships & Candidates (India & International):**")
            for item in candidates[:6]:
                dl = item["application_deadline"] or "Check official portal"
                dests = ", ".join(item.get("destination_countries") or [])
                lines.append(
                    f"- **{item['name']}** ({dests} • {item['funding_type'].replace('_', ' ')}) — "
                    f"**{item['eligibility_label']}** | Status: {item['status']} | Deadline: {dl}\n"
                    f"  Official link: {item['official_info_url']}"
                )
                if item.get("missing_fields"):
                    lines.append(
                        f"  _Missing profile details:_ {', '.join(f.replace('_', ' ') for f in item['missing_fields'])}"
                    )
        else:
            lines.append("No matching catalogue records found for those exact filters.")

        if ruled_out:
            lines.append("")
            lines.append(
                f"_Ruled out based on current profile ({len(ruled_out)}):_ "
                + ", ".join(r["name"] for r in ruled_out[:4])
            )

        tools.retrieve_guideline_evidence(scholarship_id or "", message)
        web_res = tools.discover_and_verify_official_web(
            query=message,
            destination_country=dest_country,
            education_level=intent["education_level"],
            study_scope=intent["study_scope"],
        )
        verified_web = web_res.get("verified_results", [])
        unreachable_web = web_res.get("unreachable_results", [])
        if verified_web:
            lines.append("")
            lines.append("**Live Official Website Verification:**")
            for w in verified_web[:4]:
                ts = w["checked_at"].strftime("%Y-%m-%d %H:%M UTC")
                lines.append(f"- **{w['title']}** (HTTP {w['http_status']} verified {ts}) — {w['url']}")
                if w.get("excerpt"):
                    snippet = w["excerpt"][:240].replace("\n", " ")
                    lines.append(f"  > {snippet}...")
        if unreachable_web:
            lines.append("")
            lines.append("**Official Websites Not Reachable Right Now (not guessed):**")
            for u in unreachable_web[:3]:
                lines.append(f"- {u['title']} ({u['url']}): {u['error']}")

    if tools.collected_citations:
        lines.append("")
        lines.append("**Retrieved Evidence Passages:**")
        for idx, c in enumerate(tools.collected_citations[:4], start=1):
            page_txt = f", Page {c.page_number}" if c.page_number else ""
            lines.append(f"{idx}. **{c.title}**{page_txt} ({c.source_url})")

    return AssistantChatResponse(
        reply="\n".join(lines),
        mode=mode,
        citations=tools.collected_citations,
        live_verifications=tools.live_verifications,
        tool_calls_used=tools.tool_calls_used,
        gemini_configured=False if mode == "fallback_no_key" else True,
        disclaimer=(
            "Eligibility evaluations are preliminary and deterministic. Always verify final requirements "
            "and submit applications directly on the official provider portal."
        ),
    )
