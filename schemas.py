from datetime import date, datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, EmailStr, field_validator

VALID_BILLING_CYCLES = {"monthly", "yearly"}
VALID_STATUSES = {"active", "inactive", "cancelled"}
VALID_CATEGORIES = {"DevOps", "Communication", "Productivity", "Security", "Analytics", "Design", "Other"}


# ── Auth ──────────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserOut(BaseModel):
    id: int
    email: str
    created_at: datetime

    class Config:
        from_attributes = True


# ── Subscriptions ─────────────────────────────────────────────────────────────

class SubscriptionCreate(BaseModel):
    tool_name: str
    purchase_date: date
    billing_cycle: str
    renewal_date: date
    cost: float
    category: str = "Other"
    status: str = "active"
    description: Optional[str] = None
    currency: str = "USD"

    @field_validator("billing_cycle")
    @classmethod
    def validate_billing_cycle(cls, v: str) -> str:
        if v not in VALID_BILLING_CYCLES:
            raise ValueError(f"billing_cycle must be one of {VALID_BILLING_CYCLES}")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in VALID_STATUSES:
            raise ValueError(f"status must be one of {VALID_STATUSES}")
        return v

    @field_validator("cost")
    @classmethod
    def validate_cost(cls, v: float) -> float:
        if v < 0:
            raise ValueError("cost must be non-negative")
        return round(v, 2)

class SubscriptionUpdate(BaseModel):
    tool_name: Optional[str] = None
    purchase_date: Optional[date] = None
    billing_cycle: Optional[str] = None
    renewal_date: Optional[date] = None
    cost: Optional[float] = None
    category: Optional[str] = None
    status: Optional[str] = None
    description: Optional[str] = None
    currency: Optional[str] = None

class SubscriptionOut(BaseModel):
    id: int
    tool_name: str
    purchase_date: date
    billing_cycle: str
    renewal_date: date
    cost: float
    category: str
    status: str
    description: Optional[str]
    currency: str
    created_at: datetime
    days_until_renewal: Optional[int] = None   # computed on demand

    class Config:
        from_attributes = True


# ── Dashboard ─────────────────────────────────────────────────────────────────

class UpcomingRenewal(BaseModel):
    id: int
    tool_name: str
    category: str
    renewal_date: date
    cost: float
    currency: str
    billing_cycle: str
    days_until_renewal: int

class OverdueSubscription(BaseModel):
    id: int
    tool_name: str
    category: str
    renewal_date: date
    cost: float
    days_overdue: int

class CategorySpend(BaseModel):
    category: str
    total_cost: float
    subscription_count: int
    percentage_of_total: float

class DashboardOut(BaseModel):
    # Counts
    total_subscriptions: int
    active_subscriptions: int
    inactive_subscriptions: int
    cancelled_subscriptions: int

    # Cost summary
    total_monthly_cost: float          # sum of monthly billing subs
    total_yearly_cost: float           # sum of yearly billing subs
    total_annual_cost: float           # normalized: monthly*12 + yearly
    average_cost_per_subscription: float

    # Renewals
    upcoming_renewals_7_days: List[UpcomingRenewal]
    upcoming_renewals_30_days: List[UpcomingRenewal]
    overdue_subscriptions: List[OverdueSubscription]

    # Rankings
    top_5_expensive: List[SubscriptionOut]
    spend_by_category: List[CategorySpend]
    spend_by_billing_cycle: Dict[str, float]

    # Recent activity
    subscriptions_added_this_month: int


# ── Analytics ─────────────────────────────────────────────────────────────────

class MonthlySpend(BaseModel):
    month: str        # "2025-03"
    total_cost: float
    subscription_count: int

class CostOptimizationTip(BaseModel):
    tool_name: str
    current_cost: float
    billing_cycle: str
    suggestion: str
    potential_savings: float

class AnalyticsOut(BaseModel):
    monthly_spend_trend: List[MonthlySpend]
    cost_optimization_tips: List[CostOptimizationTip]
    most_used_categories: List[CategorySpend]
    renewal_density: Dict[str, int]   # month → count of renewals


# ── Chat ──────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    reply: str

class ChatMessageOut(BaseModel):
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True

class QuickPrompt(BaseModel):
    label: str
    prompt: str
    description: str
