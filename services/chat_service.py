"""
chat_service.py
---------------
LangChain-powered AI agent with full tool-calling and agentic loop.

LLM Backend  : ChatGroq (llama-3.3-70b-versatile) by default
               Switch to ChatOpenAI by setting MODEL_PROVIDER=openai in .env
AI Framework : LangChain — AgentExecutor + create_tool_calling_agent
Tools        : 7 live subscription tools + DuckDuckGo web search (LangChain Community)
Memory       : Short-term (in-memory) + Long-term (SQLite UserPreference) via memory_service

Environment variables:
  GROQ_API_KEY    — required for Groq (default)
  MODEL_PROVIDER  — "groq" (default) | "openai"
  LLM_MODEL       — model name (default: llama-3.3-70b-versatile for Groq, gpt-4o for OpenAI)
  OPENAI_API_KEY  — required only when MODEL_PROVIDER=openai
"""
import json
import logging
import os
from collections import defaultdict
from datetime import date, timedelta

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import StructuredTool
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

import models
from services import memory_service
from services.search_service import search_web

load_dotenv()
logger = logging.getLogger(__name__)

# ── LLM Factory ───────────────────────────────────────────────────────────────

def _get_llm():
    """Return a LangChain chat model based on MODEL_PROVIDER env var."""
    provider = os.getenv("MODEL_PROVIDER", "groq").lower()
    if provider == "openai":
        from langchain_openai import ChatOpenAI
        model = os.getenv("LLM_MODEL", "gpt-4o")
        logger.info("[LLM] Provider: OpenAI | Model: %s", model)
        return ChatOpenAI(
            model=model,
            api_key=os.getenv("OPENAI_API_KEY"),
            temperature=0.1,
            max_tokens=2048,
        )
    else:
        from langchain_groq import ChatGroq
        model = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
        logger.info("[LLM] Provider: Groq | Model: %s", model)
        return ChatGroq(
            model=model,
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.1,
            max_tokens=2048,
        )


# ── System Prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an intelligent Subscription Management Assistant for an organization's tool dashboard.

Your role:
- Help users understand their software subscriptions, costs, and renewal timelines
- Identify cost-saving opportunities and potential optimizations
- Provide data-driven insights using live subscription data via available tools
- Search the web for real-time pricing, alternatives, and feature comparisons when needed

Guidelines:
- ALWAYS call the relevant tool before answering questions about subscriptions or costs
- Be concise, professional, and data-driven in your responses
- Format currency as $X.XX and dates as YYYY-MM-DD
- Use the web search tool when asked about pricing, alternatives, or market comparisons
- Proactively flag urgent items (overdue or renewing within 7 days)
- Provide actionable recommendations backed by live data, not guesses"""


def _build_system(user_context: str = "") -> str:
    system = SYSTEM_PROMPT
    if user_context:
        system += f"\n\nUser context from previous sessions:\n{user_context}"
    return system


# ── Raw Data Functions (tool implementations) ─────────────────────────────────

def _get_all_subscriptions(user_id: int, db: Session, status_filter: str = "") -> list:
    q = db.query(models.Subscription).filter(models.Subscription.user_id == user_id)
    if status_filter:
        q = q.filter(models.Subscription.status == status_filter)
    return [
        {
            "id": s.id,
            "tool_name": s.tool_name,
            "category": s.category,
            "billing_cycle": s.billing_cycle,
            "purchase_date": str(s.purchase_date),
            "renewal_date": str(s.renewal_date),
            "cost": s.cost,
            "currency": s.currency,
            "status": s.status,
            "description": s.description,
            "days_until_renewal": (s.renewal_date - date.today()).days,
        }
        for s in q.all()
    ]


def _get_dashboard_summary(user_id: int, db: Session) -> dict:
    subs = db.query(models.Subscription).filter(models.Subscription.user_id == user_id).all()
    active = [s for s in subs if s.status == "active"]
    today = date.today()
    monthly = sum(s.cost for s in active if s.billing_cycle == "monthly")
    yearly = sum(s.cost for s in active if s.billing_cycle == "yearly")
    annual = round(monthly * 12 + yearly, 2)
    upcoming_7 = [s for s in active if today <= s.renewal_date <= today + timedelta(days=7)]
    upcoming_30 = [s for s in active if today <= s.renewal_date <= today + timedelta(days=30)]
    overdue = [s for s in active if s.renewal_date < today]
    top5 = sorted(active, key=lambda x: x.cost, reverse=True)[:5]
    cat_totals: dict = defaultdict(float)
    for s in active:
        cat_totals[s.category] += s.cost
    return {
        "total_subscriptions": len(subs),
        "active": len(active),
        "inactive": len([s for s in subs if s.status == "inactive"]),
        "cancelled": len([s for s in subs if s.status == "cancelled"]),
        "total_monthly_cost": round(monthly, 2),
        "total_yearly_cost": round(yearly, 2),
        "total_annual_cost": annual,
        "daily_cost": round(annual / 365, 2) if annual > 0 else 0,
        "upcoming_7_days": [{"tool": s.tool_name, "renewal_date": str(s.renewal_date), "cost": s.cost} for s in upcoming_7],
        "upcoming_30_days_count": len(upcoming_30),
        "overdue_count": len(overdue),
        "overdue_tools": [{"tool": s.tool_name, "renewal_date": str(s.renewal_date)} for s in overdue],
        "top_5_expensive": [{"tool_name": s.tool_name, "cost": s.cost, "billing_cycle": s.billing_cycle} for s in top5],
        "spend_by_category": {cat: round(t, 2) for cat, t in sorted(cat_totals.items(), key=lambda x: x[1], reverse=True)},
    }


def _get_upcoming_renewals(user_id: int, db: Session, days: int = 7) -> list:
    today = date.today()
    cutoff = today + timedelta(days=days)
    subs = db.query(models.Subscription).filter(
        models.Subscription.user_id == user_id,
        models.Subscription.status == "active",
        models.Subscription.renewal_date >= today,
        models.Subscription.renewal_date <= cutoff,
    ).all()
    return [
        {
            "tool_name": s.tool_name,
            "category": s.category,
            "renewal_date": str(s.renewal_date),
            "cost": s.cost,
            "currency": s.currency,
            "days_until_renewal": (s.renewal_date - today).days,
        }
        for s in sorted(subs, key=lambda x: x.renewal_date)
    ]


def _get_expensive_tools(user_id: int, db: Session, limit: int = 5, billing_cycle: str = "") -> list:
    q = db.query(models.Subscription).filter(
        models.Subscription.user_id == user_id,
        models.Subscription.status == "active",
    )
    if billing_cycle:
        q = q.filter(models.Subscription.billing_cycle == billing_cycle)
    subs = sorted(q.all(), key=lambda x: x.cost, reverse=True)[:limit]
    return [
        {"tool_name": s.tool_name, "cost": s.cost, "billing_cycle": s.billing_cycle, "category": s.category}
        for s in subs
    ]


def _get_overdue_subscriptions(user_id: int, db: Session) -> list:
    today = date.today()
    subs = db.query(models.Subscription).filter(
        models.Subscription.user_id == user_id,
        models.Subscription.status == "active",
        models.Subscription.renewal_date < today,
    ).all()
    return [
        {
            "tool_name": s.tool_name,
            "category": s.category,
            "renewal_date": str(s.renewal_date),
            "cost": s.cost,
            "days_overdue": (today - s.renewal_date).days,
        }
        for s in sorted(subs, key=lambda x: x.renewal_date)
    ]


def _get_spend_by_category(user_id: int, db: Session) -> dict:
    subs = db.query(models.Subscription).filter(
        models.Subscription.user_id == user_id,
        models.Subscription.status == "active",
    ).all()
    totals: dict = defaultdict(lambda: {"cost": 0.0, "count": 0})
    for s in subs:
        totals[s.category]["cost"] += s.cost
        totals[s.category]["count"] += 1
    return {
        cat: {"total_cost": round(v["cost"], 2), "subscription_count": v["count"]}
        for cat, v in sorted(totals.items(), key=lambda x: x[1]["cost"], reverse=True)
    }


# ── Pydantic Input Schemas for LangChain Tools ────────────────────────────────

class StatusFilterInput(BaseModel):
    status_filter: str = Field(default="", description="Optional: 'active', 'inactive', or 'cancelled'")

class DaysInput(BaseModel):
    days: int = Field(default=7, description="Number of days to look ahead")

class ExpensiveToolsInput(BaseModel):
    limit: int = Field(default=5, description="How many top tools to return")
    billing_cycle: str = Field(default="", description="Filter by 'monthly' or 'yearly'")

class WebSearchInput(BaseModel):
    query: str = Field(description="Search query, e.g. 'GitHub pricing plans 2024'")
    max_results: int = Field(default=4, description="Number of results to return")

class EmptyInput(BaseModel):
    pass


# ── LangChain Tool Builder ────────────────────────────────────────────────────

def _build_tools(user_id: int, db: Session) -> list:
    """
    Build LangChain StructuredTools with user_id and db injected via closures.
    Each tool wraps a raw data function and serialises the result to JSON string.
    """

    def get_all_subscriptions(status_filter: str = "") -> str:
        result = _get_all_subscriptions(user_id, db, status_filter)
        return json.dumps(result, default=str)

    def get_dashboard_summary() -> str:
        result = _get_dashboard_summary(user_id, db)
        return json.dumps(result, default=str)

    def get_upcoming_renewals(days: int = 7) -> str:
        result = _get_upcoming_renewals(user_id, db, days)
        return json.dumps(result, default=str)

    def get_expensive_tools(limit: int = 5, billing_cycle: str = "") -> str:
        result = _get_expensive_tools(user_id, db, limit, billing_cycle)
        return json.dumps(result, default=str)

    def get_overdue_subscriptions() -> str:
        result = _get_overdue_subscriptions(user_id, db)
        return json.dumps(result, default=str)

    def get_spend_by_category() -> str:
        result = _get_spend_by_category(user_id, db)
        return json.dumps(result, default=str)

    def search_web_for_tool_info(query: str, max_results: int = 4) -> str:
        results = search_web(query, max_results)
        return json.dumps(results, default=str)

    return [
        StructuredTool.from_function(
            func=get_all_subscriptions,
            name="get_all_subscriptions",
            description="Retrieve all user subscriptions with cost, billing cycle, category, status, and renewal date.",
            args_schema=StatusFilterInput,
        ),
        StructuredTool.from_function(
            func=get_dashboard_summary,
            name="get_dashboard_summary",
            description="Full analytics dashboard: annual cost, monthly/yearly breakdown, active/inactive counts, upcoming renewals (7 & 30 days), overdue tools, spend by category, top 5 most expensive.",
            args_schema=EmptyInput,
        ),
        StructuredTool.from_function(
            func=get_upcoming_renewals,
            name="get_upcoming_renewals",
            description="Subscriptions renewing within N days (default 7). Use 30 for a monthly view.",
            args_schema=DaysInput,
        ),
        StructuredTool.from_function(
            func=get_expensive_tools,
            name="get_expensive_tools",
            description="Top N most expensive active subscriptions, optionally filtered by billing cycle.",
            args_schema=ExpensiveToolsInput,
        ),
        StructuredTool.from_function(
            func=get_overdue_subscriptions,
            name="get_overdue_subscriptions",
            description="Subscriptions whose renewal date has already passed — need immediate attention.",
            args_schema=EmptyInput,
        ),
        StructuredTool.from_function(
            func=get_spend_by_category,
            name="get_spend_by_category",
            description="Total monthly spend broken down by category (DevOps, Communication, Security, etc.).",
            args_schema=EmptyInput,
        ),
        StructuredTool.from_function(
            func=search_web_for_tool_info,
            name="search_web_for_tool_info",
            description="Search DuckDuckGo for real-time tool info: pricing, alternatives, feature comparisons. Use when the user asks about market prices or alternatives.",
            args_schema=WebSearchInput,
        ),
    ]


# ── Main Chat Processor ───────────────────────────────────────────────────────

def process_chat(user_id: int, message: str, db: Session) -> str:
    """
    Process a user message through the LangChain tool-calling agent.

    Flow:
      1. Load long-term preferences → enrich system prompt
      2. Load short-term history → convert to LangChain HumanMessage/AIMessage
      3. Build tools (closures over user_id + db)
      4. Create LangChain agent (create_tool_calling_agent + AgentExecutor)
      5. Run agent → automatic agentic loop (LLM ↔ tools)
      6. Save result to memory (short-term + long-term)
    """
    llm = _get_llm()

    # Enrich system prompt with long-term preferences
    prefs = memory_service.get_all_preferences(user_id, db)
    user_context = "\n".join(f"  - {k}: {v}" for k, v in prefs.items()) if prefs else ""
    system_prompt = _build_system(user_context)

    # Build LangGraph ReAct agent (handles tool-calling loop automatically)
    tools = _build_tools(user_id, db)
    agent = create_react_agent(model=llm, tools=tools, prompt=system_prompt)

    # Convert stored history to LangChain message objects
    history = memory_service.get_conversation_history(user_id, db)
    lc_history = []
    for msg in history:
        if msg["role"] == "user":
            lc_history.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            lc_history.append(AIMessage(content=msg["content"]))

    # Run the agentic loop (LangGraph handles iterations automatically)
    try:
        result = agent.invoke({"messages": lc_history + [HumanMessage(content=message)]})
        # Last message in the graph output is the final AI response
        final_reply = result["messages"][-1].content or "I'm sorry, I couldn't generate a response."
    except Exception as e:
        logger.error("[ChatService] Agent error: %s", e)
        final_reply = f"I encountered an error processing your request. Please try again. ({type(e).__name__})"

    # Persist to memory
    memory_service.save_message(user_id, "user", message, db)
    memory_service.save_message(user_id, "assistant", final_reply, db)
    memory_service.set_preference(user_id, "last_query", message[:120], db)
    memory_service.set_preference(user_id, "last_active_date", str(date.today()), db)

    return final_reply
