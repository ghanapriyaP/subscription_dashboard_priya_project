import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from database import engine, SessionLocal
import models
from routers import auth, subscriptions, dashboard, chat, analytics
from services.scheduler import start_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# Create all DB tables
models.Base.metadata.create_all(bind=engine)

_scheduler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _scheduler
    _scheduler = start_scheduler(SessionLocal)
    yield
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)


app = FastAPI(
    title="Tool Subscription Management Dashboard",
    description=(
        "## Overview\n"
        "A centralized system to **track, manage, and optimize** your organization's "
        "software tool subscriptions.\n\n"
        "### Features\n"
        "- **Subscription CRUD** — Add, edit, delete, search, and filter subscriptions\n"
        "- **Rich Dashboard** — 12+ metrics: annual cost, overdue alerts, category breakdown\n"
        "- **Analytics** — Spend trends, cost optimization tips, renewal density\n"
        "- **AI Assistant** — Natural language queries powered by Groq (llama3) with 7 tools\n"
        "- **Web Search** — Real-time tool pricing and alternatives via DuckDuckGo\n"
        "- **Memory** — Short-term conversation context + long-term user preferences\n"
        "- **Reminders** — Automated 7-day, 30-day, and overdue renewal notifications\n\n"
        "### Auth\n"
        "All endpoints (except `/auth/*`, `/chat/prompts`, `/`) require a **Bearer token**. "
        "Register at `/auth/register` then use the token."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(subscriptions.router)
app.include_router(dashboard.router)
app.include_router(analytics.router)
app.include_router(chat.router)


@app.get("/app", include_in_schema=False, summary="Frontend dashboard")
def serve_frontend():
    return FileResponse("frontend/index.html")


@app.get("/", tags=["Root"], summary="API information")
def root():
    return {
        "name": "Tool Subscription Management Dashboard API",
        "version": "2.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "endpoints": {
            "authentication": {
                "POST /auth/register": "Create account, receive JWT token",
                "POST /auth/login": "Login, receive JWT token",
                "GET /auth/me": "Current user info",
            },
            "subscriptions": {
                "GET /subscriptions/": "List with filters: status, category, billing_cycle, search, sort, pagination",
                "GET /subscriptions/{id}": "Get single subscription",
                "POST /subscriptions/": "Add subscription (name, dates, cost, category, status)",
                "PUT /subscriptions/{id}": "Update subscription",
                "DELETE /subscriptions/{id}": "Delete subscription",
            },
            "dashboard": {
                "GET /dashboard/": "Full analytics: 12+ metrics including annual cost, overdue, category spend",
            },
            "analytics": {
                "GET /analytics/": "Deep analytics: spend trends, cost optimization tips, renewal density",
                "GET /analytics/summary": "Quick spend summary in plain numbers",
            },
            "chat_assistant": {
                "POST /chat/": "Chat with AI assistant (natural language subscription queries)",
                "GET /chat/prompts": "8 predefined quick-access prompts (no auth needed)",
                "GET /chat/history": "Conversation history",
                "DELETE /chat/history": "Clear history and reset memory",
            },
        },
        "subscription_categories": ["DevOps", "Communication", "Productivity", "Security", "Analytics", "Design", "Other"],
        "billing_cycles": ["monthly", "yearly"],
        "subscription_statuses": ["active", "inactive", "cancelled"],
    }
