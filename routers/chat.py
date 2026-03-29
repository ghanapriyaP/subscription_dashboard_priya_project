from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from services import chat_service, memory_service
import models
import schemas

router = APIRouter(prefix="/chat", tags=["Chat Assistant"])

# ── Predefined quick-access prompts ──────────────────────────────────────────
QUICK_PROMPTS = [
    schemas.QuickPrompt(
        label="Upcoming Renewals",
        prompt="Which of my tools are due for renewal in the next 7 days?",
        description="Check tools renewing this week",
    ),
    schemas.QuickPrompt(
        label="Monthly Spend",
        prompt="How much am I spending on tools this month? Give me a full breakdown.",
        description="View total monthly spending",
    ),
    schemas.QuickPrompt(
        label="Expensive Tools",
        prompt="What are the top 5 most expensive tools I'm subscribed to?",
        description="Identify highest-cost subscriptions",
    ),
    schemas.QuickPrompt(
        label="Cost Optimization",
        prompt="Analyze my subscriptions and suggest ways I can reduce costs or switch to better plans.",
        description="Get AI cost-saving recommendations",
    ),
    schemas.QuickPrompt(
        label="Overdue Renewals",
        prompt="Do I have any subscriptions that are past their renewal date?",
        description="Find overdue subscriptions needing attention",
    ),
    schemas.QuickPrompt(
        label="Spend by Category",
        prompt="Break down my subscription spending by category.",
        description="See spending grouped by tool category",
    ),
    schemas.QuickPrompt(
        label="30-Day Outlook",
        prompt="Show me everything renewing in the next 30 days and the total cost due.",
        description="Monthly renewal forecast",
    ),
    schemas.QuickPrompt(
        label="Annual Cost",
        prompt="What is my total annual spend on all tools? Include a monthly equivalent.",
        description="See normalized annual spending",
    ),
]


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/", response_model=schemas.ChatResponse, summary="Send a message to the AI assistant")
def chat(
    payload: schemas.ChatRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    reply = chat_service.process_chat(current_user.id, payload.message, db)
    return {"reply": reply}


@router.get("/prompts", response_model=List[schemas.QuickPrompt], summary="Get predefined quick-access prompts")
def get_quick_prompts():
    """Returns predefined prompts for common subscription queries — no auth required."""
    return QUICK_PROMPTS


@router.get("/history", response_model=List[schemas.ChatMessageOut], summary="Get chat history")
def get_history(
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    messages = (
        db.query(models.ChatMessage)
        .filter(models.ChatMessage.user_id == current_user.id)
        .order_by(models.ChatMessage.created_at.desc())
        .limit(limit)
        .all()
    )
    return list(reversed(messages))


@router.delete("/history", status_code=204, summary="Clear chat history and reset memory")
def clear_history(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    db.query(models.ChatMessage).filter(models.ChatMessage.user_id == current_user.id).delete()
    db.commit()
    memory_service.clear_short_term(current_user.id)
