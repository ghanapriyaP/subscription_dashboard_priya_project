# Tool Subscription Management Dashboard

A full-stack backend system to **track, manage, and optimize** your organization's software tool subscriptions — with an AI-powered assistant, real-time analytics, and automated renewal reminders.

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [How to Run](#how-to-run)
- [Environment Variables](#environment-variables)
- [Frontend](#frontend)
- [API Reference](#api-reference)
- [AI Assistant](#ai-assistant)
- [Automated Reminders](#automated-reminders)
- [Database Schema](#database-schema)

---

## Features

| Feature | Details |
|---|---|
| **Auth** | JWT Bearer tokens — register, login, protected routes |
| **Subscription CRUD** | Add, edit, delete, search, filter, paginate subscriptions |
| **Dashboard** | 12+ metrics: annual cost, overdue alerts, category breakdown, top-5 expensive |
| **Analytics** | Spend trends, cost optimization tips, renewal density calendar |
| **AI Assistant** | Natural language queries via LangChain + Groq (llama-3.3-70b) with 7 live tools |
| **Web Search** | Real-time tool pricing and alternatives via DuckDuckGo |
| **Memory** | Short-term (in-memory last 10 messages) + long-term (SQLite UserPreference) |
| **Reminders** | APScheduler — automated 7-day, 30-day, and overdue renewal notifications |
| **Frontend** | Single-page app: Dashboard, Subscriptions, Analytics, AI Chat — no framework needed |

---

## Tech Stack

| Layer | Technology |
|---|---|
| **API Framework** | FastAPI 0.100+ |
| **Database** | SQLite via SQLAlchemy ORM |
| **Auth** | JWT (python-jose) + bcrypt password hashing |
| **AI Framework** | LangChain 1.x + LangGraph ReAct agent |
| **LLM Provider** | Groq (`llama-3.3-70b-versatile`) — or OpenAI (`gpt-4o`) via env toggle |
| **Web Search** | DuckDuckGo Search (langchain-community) |
| **Scheduler** | APScheduler BackgroundScheduler |
| **Frontend** | Vanilla JS + Tailwind CSS CDN + Chart.js + Font Awesome |
| **Server** | Uvicorn (ASGI) |

---

## Project Structure

```
assign-subbu-anna/
├── app.py                        # FastAPI entry point — routers, CORS, lifespan, frontend serving
├── database.py                   # SQLAlchemy engine, SessionLocal, Base, get_db dependency
├── models.py                     # ORM models: User, Subscription, ChatMessage, UserPreference
├── schemas.py                    # Pydantic schemas: request/response validation
├── auth.py                       # JWT utilities: create_access_token, get_current_user
├── requirements.txt              # All Python dependencies
├── .env                          # Environment variables (API keys, secret key)
│
├── routers/
│   ├── __init__.py
│   ├── auth.py                   # POST /auth/register, POST /auth/login, GET /auth/me
│   ├── subscriptions.py          # Full CRUD + filtering + pagination for /subscriptions
│   ├── dashboard.py              # GET /dashboard — 12+ aggregated metrics
│   ├── analytics.py              # GET /analytics, GET /analytics/summary
│   └── chat.py                   # POST /chat, GET /chat/history, DELETE /chat/history
│
├── services/
│   ├── __init__.py
│   ├── chat_service.py           # LangChain ReAct agent with 7 tools + LLM factory
│   ├── memory_service.py         # Short-term + long-term conversation memory
│   ├── scheduler.py              # APScheduler jobs: 7-day, 30-day, overdue alerts
│   └── search_service.py         # DuckDuckGo web search wrapper
│
├── frontend/
│   └── index.html                # Single-page app (SPA) — served at GET /app
│
├── subscriptions.db              # Auto-created SQLite database
└── smoke_test.py                 # Quick import/sanity check script
```

---

## How to Run

### Prerequisites

- Python **3.10+**
- A free **Groq API key** — get one at [console.groq.com](https://console.groq.com) (free, no credit card)

---

### Step 1 — Clone the repository

```bash
git clone <your-repo-url>
cd assign-subbu-anna
```

---

### Step 2 — Create and activate a virtual environment

**Windows:**
```cmd
python -m venv .venv
.venv\Scripts\activate
```

**macOS / Linux:**
```bash
python -m venv .venv
source .venv/bin/activate
```

You should see `(.venv)` in your terminal prompt after activation.

---

### Step 3 — Install dependencies

```bash
pip install -r requirements.txt
```

This installs FastAPI, SQLAlchemy, LangChain, Groq, APScheduler, and all other packages.

---

### Step 4 — Create the `.env` file

Create a file named `.env` in the project root:

```env
GROQ_API_KEY=gsk_your_groq_api_key_here
SECRET_KEY=any-long-random-string-for-jwt

# LLM settings (defaults below work out of the box with Groq)
MODEL_PROVIDER=groq
LLM_MODEL=llama-3.3-70b-versatile

# Uncomment below if you want to use OpenAI instead
# MODEL_PROVIDER=openai
# LLM_MODEL=gpt-4o
# OPENAI_API_KEY=sk-your-openai-key
```

> **Tip:** Replace `gsk_your_groq_api_key_here` with your actual Groq key. The database (`subscriptions.db`) is created automatically on first run — no setup needed.

---

### Step 5 — Start the server

```bash
uvicorn app:app --reload
```

You should see output like:

```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Application startup complete.
[Scheduler] Started. Jobs: 7-day reminders, 30-day reminders, overdue alerts.
```

---

### Step 6 — Open the Frontend

Open your browser and go to:

```
http://localhost:8000/app
```

That's it! You'll see the full dashboard UI.

| URL | What it is |
|---|---|
| **`http://localhost:8000/app`** | **Frontend SPA — start here** |
| `http://localhost:8000/docs` | Swagger UI (interactive API explorer) |
| `http://localhost:8000/redoc` | ReDoc API docs |
| `http://localhost:8000/` | API health/info JSON |

---

### Test Credentials (pre-seeded data)

A test account with 10 sample subscriptions is already loaded in the database:

| Field | Value |
|---|---|
| **Email** | `test@gmail.com` |
| **Password** | `test123@` |

Pre-seeded subscriptions: GitHub, Slack, Figma, Notion, AWS, Datadog, Zoom, 1Password, Jira, Sentry — covering DevOps, Communication, Design, Productivity, Analytics, and Security categories.

> **Note:** Jira is overdue (-5 days) and AWS + Figma are renewing within 7 days — so all alert banners will fire on the dashboard.

---

### First Time Using the App

**Option A — Use the test account (instant demo):**
1. Go to `http://localhost:8000/app`
2. Click **Login** tab → enter `test@gmail.com` / `test123@` → click **Sign In**
3. You're in! Dashboard shows real data immediately

**Option B — Create your own account:**
1. Go to `http://localhost:8000/app`
2. Click **Register** tab → enter any email + password → click **Create Account**
3. You're in! The dashboard loads automatically
4. Go to **Subscriptions** → **Add New** to add your first tool
5. Head to **AI Chat** and ask: *"What is my total annual spend?"*

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `GROQ_API_KEY` | Yes (if Groq) | — | Groq API key from console.groq.com |
| `SECRET_KEY` | Yes | — | JWT signing secret — change in production |
| `MODEL_PROVIDER` | No | `groq` | `groq` or `openai` |
| `LLM_MODEL` | No | `llama-3.3-70b-versatile` | Model name for chosen provider |
| `OPENAI_API_KEY` | Only if OpenAI | — | OpenAI API key |

---

## API Reference

All endpoints except `/auth/*`, `/chat/prompts`, and `/` require a **Bearer token** in the `Authorization` header.

### Authentication

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/auth/register` | No | Register with email + password, returns JWT token |
| `POST` | `/auth/login` | No | Login, returns JWT token |
| `GET` | `/auth/me` | Yes | Returns current user info |

**Register example:**
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "secret123"}'
```

**Response:**
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer"
}
```

---

### Subscriptions

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/subscriptions/` | Yes | List with filters, sorting, pagination |
| `GET` | `/subscriptions/{id}` | Yes | Get single subscription |
| `POST` | `/subscriptions/` | Yes | Create new subscription |
| `PUT` | `/subscriptions/{id}` | Yes | Update subscription |
| `DELETE` | `/subscriptions/{id}` | Yes | Delete subscription |

**Query Parameters for `GET /subscriptions/`:**

| Param | Type | Description |
|---|---|---|
| `status` | string | Filter: `active` \| `inactive` \| `cancelled` |
| `category` | string | Filter by category |
| `billing_cycle` | string | Filter: `monthly` \| `yearly` |
| `search` | string | Search tool name (case-insensitive) |
| `renewing_in_days` | int | Only subscriptions renewing within N days |
| `sort_by` | string | `cost` \| `renewal_date` \| `tool_name` \| `created_at` |
| `sort_order` | string | `asc` \| `desc` |
| `page` | int | Page number (default: 1) |
| `page_size` | int | Items per page (default: 20, max: 100) |

**Subscription fields:**

| Field | Type | Required | Values |
|---|---|---|---|
| `tool_name` | string | Yes | e.g., "GitHub", "Slack" |
| `purchase_date` | date | Yes | `YYYY-MM-DD` |
| `billing_cycle` | string | Yes | `monthly` \| `yearly` |
| `renewal_date` | date | Yes | `YYYY-MM-DD` |
| `cost` | float | Yes | e.g., `49.99` |
| `category` | string | No | `DevOps` \| `Communication` \| `Productivity` \| `Security` \| `Analytics` \| `Design` \| `Other` |
| `status` | string | No | `active` \| `inactive` \| `cancelled` |
| `description` | string | No | Free text |
| `currency` | string | No | Default: `USD` |

---

### Dashboard

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/dashboard/` | Yes | Full analytics — 12+ metrics |

**Response includes:**
- `total_subscriptions`, `active`, `inactive`, `cancelled` counts
- `total_monthly_cost`, `total_yearly_cost`, `total_annual_cost`, `daily_cost`
- `upcoming_7_days` — list of tools renewing this week
- `upcoming_30_days_count` — count renewing this month
- `overdue_count`, `overdue_tools` — past renewal date
- `top_5_expensive` — highest cost active subscriptions
- `spend_by_category` — cost breakdown per category

---

### Analytics

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/analytics/` | Yes | Deep analytics: trends, optimization tips, renewal density |
| `GET` | `/analytics/summary` | Yes | Quick plain-number spend summary |

**`/analytics/` response includes:**
- `spend_trends` — monthly spend over time
- `potential_savings` — cost optimization recommendations
- `renewal_density` — how many renewals per month
- `category_analysis` — per-category stats
- `billing_cycle_distribution` — monthly vs yearly split

---

### Chat (AI Assistant)

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/chat/` | Yes | Chat with AI assistant |
| `GET` | `/chat/prompts` | No | 8 predefined quick-access prompts |
| `GET` | `/chat/history` | Yes | Conversation history |
| `DELETE` | `/chat/history` | Yes | Clear history and reset memory |

**Chat request:**
```json
{
  "message": "What are my most expensive subscriptions this month?"
}
```

**Chat response:**
```json
{
  "reply": "Your top 3 most expensive subscriptions are: ..."
}
```

---

## Frontend

The frontend is a **single-page application (SPA)** built with Vanilla JS + Tailwind CSS CDN + Chart.js, served directly by FastAPI — no separate build step or Node.js required.

### How to Open

```
http://localhost:8000/app
```

Just start the backend server (Step 5 above) and open that URL in your browser.

### Design

- Dark gradient sidebar (`#0f172a → #1e1b4b`) with glowing active nav items
- Gradient KPI cards (indigo, emerald, amber, rose, blue, violet)
- Frosted-glass sticky topbar
- Smooth hover animations on cards and buttons
- Color-coded renewal urgency (red = overdue/≤7 days, amber = ≤30 days, gray = safe)
- Toast notifications for all actions (top-right)
- Empty states with icons when no data
- Loading spinners on all async operations

### Views

| View | What you can do |
|---|---|
| **Dashboard** | See 4 KPI cards (annual spend, active tools, renewing soon, overdue), category donut chart, top-5 expense progress bars, 7-day renewal list, overdue list, alert banners |
| **Subscriptions** | Search by name, filter by status/category/billing/sort, paginated table, add new subscription, edit any subscription, delete with confirmation |
| **Analytics** | 4 spend KPIs, monthly spend trend (line chart), renewal density by month (bar chart), full cost optimization tips from AI analysis |
| **AI Chat** | Quick prompt chips, live chat with typing indicator, markdown formatting in bot replies, persistent history, clear conversation |

### Auth Flow

1. Open `http://localhost:8000/app` — auth screen loads automatically
2. Click **Register** → enter email + password → **Create Account**
3. JWT token is saved to `localStorage` and all API calls use it automatically
4. On return visits, you're logged in automatically if the token is still valid
5. Click **Sign Out** in the sidebar to log out

### Tech used (no build required)

- **Tailwind CSS** — loaded from CDN, utility-first styling
- **Chart.js 4.4** — donut, line, and bar charts
- **Font Awesome 6.5** — icons throughout the UI
- **Google Fonts (Inter)** — typography
- **Vanilla JS** — zero framework dependencies

---

## AI Assistant

The AI assistant uses a **LangGraph ReAct agent** (reasoning + acting loop) with 7 live tools:

| Tool | Description |
|---|---|
| `get_all_subscriptions` | Fetch all subscriptions with optional status filter |
| `get_dashboard_summary` | Full analytics: annual cost, overdue, category breakdown |
| `get_upcoming_renewals` | Subscriptions renewing within N days |
| `get_expensive_tools` | Top N most expensive active subscriptions |
| `get_overdue_subscriptions` | Subscriptions past their renewal date |
| `get_spend_by_category` | Cost breakdown per category |
| `search_web_for_tool_info` | DuckDuckGo search for real-time pricing and alternatives |

**Example questions you can ask:**
- "What is my total annual spend?"
- "Which subscriptions are renewing this week?"
- "Show me all overdue subscriptions"
- "What are cheaper alternatives to Salesforce?"
- "Which category am I spending the most on?"
- "Suggest ways to reduce my software costs"

**LLM Providers:**

| Provider | Model | How to enable |
|---|---|---|
| Groq (default) | `llama-3.3-70b-versatile` | Set `GROQ_API_KEY` in `.env` |
| OpenAI | `gpt-4o` | Set `MODEL_PROVIDER=openai` and `OPENAI_API_KEY` in `.env` |

---

## Automated Reminders

APScheduler runs background jobs on startup and every 24 hours:

| Job | Schedule | Trigger |
|---|---|---|
| 7-day renewal check | Every 24 hours | Subscription renewing within 7 days |
| 30-day renewal check | Every 24 hours | Subscription renewing in 8–30 days |
| Overdue check | Every 12 hours | Subscription past renewal date |

Notifications are printed to the server console (mock email + webhook):

```
============================================================
[EMAIL NOTIFICATION]
  To      : user@example.com
  Subject : Subscription Renewal in 3 day(s): GitHub
  Body    : Your subscription to GitHub (DevOps) renews on 2025-04-01 ...
============================================================
```

---

## Database Schema

SQLite database (`subscriptions.db`) is auto-created on first run.

```
users
  id, email (unique), hashed_password, created_at

subscriptions
  id, user_id (FK), tool_name, purchase_date, billing_cycle,
  renewal_date, cost, category, status, description, currency, created_at

chat_messages
  id, user_id (FK), role (user|assistant), content, created_at

user_preferences
  id, user_id (FK), key, value
```

---

## Development Notes

- **CORS** is set to `allow_origins=["*"]` — restrict in production
- **JWT secret** in `.env` must be changed for production
- **SQLite** is used for simplicity — swap for PostgreSQL for production
- The database file `subscriptions.db` is auto-created; delete it to reset all data
- `smoke_test.py` can be run to verify imports and basic sanity

---

## License

MIT
