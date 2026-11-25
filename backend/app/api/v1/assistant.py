from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from app.agent.coordinator import run_assistant_turn
from app.agent.tools import build_checklist_response
from app.api.deps import enforce_assistant_rate_limit, get_current_user
from app.core.config import get_settings
from app.db.session import get_db
from app.models.rag import AssistantMessage
from app.models.scholarship import Scholarship
from app.models.user import User
from app.schemas.assistant import (
    AssistantChatRequest,
    AssistantChatResponse,
    AssistantHistoryItem,
    ChecklistResponse,
    CitationSchema,
)

router = APIRouter(prefix="/assistant", tags=["assistant"])


@router.get("/status")
def assistant_status(current_user: User = Depends(get_current_user)) -> dict:
    settings = get_settings()
    return {
        "gemini_configured": settings.gemini_configured,
        "model": settings.gemini_model if settings.gemini_configured else None,
        "fallback_mode": "deterministic_rules_and_rag",
    }


@router.get("/history", response_model=list[AssistantHistoryItem])
def get_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[AssistantHistoryItem]:
    rows = list(
        db.scalars(
            select(AssistantMessage)
            .where(AssistantMessage.user_id == current_user.id)
            .order_by(AssistantMessage.created_at.asc())
            .limit(60)
        ).all()
    )
    items: list[AssistantHistoryItem] = []
    for r in rows:
        citations: list[CitationSchema] = []
        if r.citations_json:
            try:
                raw_list = json.loads(r.citations_json)
                citations = [CitationSchema.model_validate(c) for c in raw_list]
            except Exception:
                citations = []
        items.append(
            AssistantHistoryItem(
                id=r.id,
                scholarship_id=r.scholarship_id,
                role=r.role,
                content=r.content,
                citations=citations,
                mode=r.mode,
                created_at=r.created_at,
            )
        )
    return items


@router.delete("/history")
def clear_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    db.execute(delete(AssistantMessage).where(AssistantMessage.user_id == current_user.id))
    db.commit()
    return {"message": "Conversation history cleared."}


@router.post("/chat", response_model=AssistantChatResponse)
def chat(
    payload: AssistantChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(enforce_assistant_rate_limit),
) -> AssistantChatResponse:
    resolved_scholarship_id = payload.scholarship_id
    if resolved_scholarship_id:
        s = db.scalar(
            select(Scholarship).where(
                or_(
                    Scholarship.id == resolved_scholarship_id,
                    Scholarship.slug == resolved_scholarship_id,
                )
            )
        )
        if not s:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Scholarship not found."
            )
        resolved_scholarship_id = s.id

    db.add(
        AssistantMessage(
            user_id=current_user.id,
            scholarship_id=resolved_scholarship_id,
            role="user",
            content=payload.message.strip(),
            mode="user",
        )
    )
    db.flush()

    resp = run_assistant_turn(db, current_user, payload.message.strip(), resolved_scholarship_id)

    db.add(
        AssistantMessage(
            user_id=current_user.id,
            scholarship_id=resolved_scholarship_id,
            role="assistant",
            content=resp.reply,
            citations_json=json.dumps([c.model_dump() for c in resp.citations]),
            mode=resp.mode,
        )
    )
    db.commit()
    return resp


@router.get("/checklist/{scholarship_id}", response_model=ChecklistResponse)
@router.post("/checklist/{scholarship_id}", response_model=ChecklistResponse)
def get_checklist(
    scholarship_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChecklistResponse:
    s = db.scalar(
        select(Scholarship).where(
            or_(Scholarship.id == scholarship_id, Scholarship.slug == scholarship_id)
        )
    )
    if not s:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scholarship not found.")
    return build_checklist_response(s)
