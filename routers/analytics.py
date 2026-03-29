"""
analytics.py
------------
Dedicated analytics endpoint providing spend trends, cost optimization tips,
renewal density, and category breakdowns beyond the main dashboard.
"""
from collections import defaultdict
from datetime import date, timedelta
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
import models
import schemas

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/", response_model=schemas.AnalyticsOut, summary="Deep analytics: trends, cost tips, renewal density")
def get_analytics(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    active = (
        db.query(models.Subscription)
        .filter(models.Subscription.user_id == current_user.id, models.Subscription.status == "active")
        .all()
    )
    today = date.today()

    # ── Monthly spend trend (last 12 months by created_at) ────────────────────
    month_data: dict = defaultdict(lambda: {"cost": 0.0, "count": 0})
    for s in active:
        key = s.created_at.strftime("%Y-%m")
        month_data[key]["cost"] += s.cost
        month_data[key]["count"] += 1

    monthly_trend = [
        schemas.MonthlySpend(month=k, total_cost=round(v["cost"], 2), subscription_count=v["count"])
        for k, v in sorted(month_data.items())
    ]

    # ── Cost optimization tips ────────────────────────────────────────────────
    tips: List[schemas.CostOptimizationTip] = []

    for s in active:
        # Monthly → suggest yearly (typically ~17% savings)
        if s.billing_cycle == "monthly":
            annual_monthly = s.cost * 12
            potential_yearly = round(annual_monthly * 0.83, 2)   # ~17% typical yearly discount
            savings = round(annual_monthly - potential_yearly, 2)
            if savings > 0:
                tips.append(schemas.CostOptimizationTip(
                    tool_name=s.tool_name,
                    current_cost=s.cost,
                    billing_cycle="monthly",
                    suggestion=f"Switch to yearly billing to save ~${savings:.2f}/year (estimated 17% discount).",
                    potential_savings=savings,
                ))

        # High-cost tools > $200/month → flag for review
        monthly_equiv = s.cost if s.billing_cycle == "monthly" else round(s.cost / 12, 2)
        if monthly_equiv > 200:
            tips.append(schemas.CostOptimizationTip(
                tool_name=s.tool_name,
                current_cost=s.cost,
                billing_cycle=s.billing_cycle,
                suggestion=f"High-cost tool (${monthly_equiv:.2f}/mo). Consider auditing usage or finding alternatives.",
                potential_savings=0.0,
            ))

    # Sort tips: highest savings first
    tips.sort(key=lambda x: x.potential_savings, reverse=True)

    # ── Most used categories ──────────────────────────────────────────────────
    cat_map: dict = defaultdict(lambda: {"cost": 0.0, "count": 0})
    for s in active:
        cat_map[s.category]["cost"] += s.cost
        cat_map[s.category]["count"] += 1

    annual_cost = sum(
        s.cost * 12 if s.billing_cycle == "monthly" else s.cost for s in active
    )
    most_used_cats = [
        schemas.CategorySpend(
            category=cat,
            total_cost=round(v["cost"], 2),
            subscription_count=v["count"],
            percentage_of_total=round(v["cost"] / annual_cost * 100, 1) if annual_cost else 0.0,
        )
        for cat, v in sorted(cat_map.items(), key=lambda x: x[1]["count"], reverse=True)
    ]

    # ── Renewal density (next 12 months) ─────────────────────────────────────
    renewal_density: dict = defaultdict(int)
    for s in active:
        if s.renewal_date >= today:
            key = s.renewal_date.strftime("%Y-%m")
            renewal_density[key] += 1

    return schemas.AnalyticsOut(
        monthly_spend_trend=monthly_trend,
        cost_optimization_tips=tips,
        most_used_categories=most_used_cats,
        renewal_density=dict(sorted(renewal_density.items())),
    )


@router.get("/summary", summary="Quick spend summary in plain numbers")
def get_spend_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    active = (
        db.query(models.Subscription)
        .filter(models.Subscription.user_id == current_user.id, models.Subscription.status == "active")
        .all()
    )
    today = date.today()
    monthly = sum(s.cost for s in active if s.billing_cycle == "monthly")
    yearly = sum(s.cost for s in active if s.billing_cycle == "yearly")
    annual = round(monthly * 12 + yearly, 2)
    due_soon = [s for s in active if today <= s.renewal_date <= today + timedelta(days=30)]

    return {
        "active_tools": len(active),
        "monthly_spend": round(monthly, 2),
        "yearly_spend": round(yearly, 2),
        "total_annual_spend": annual,
        "daily_cost": round(annual / 365, 2),
        "tools_renewing_in_30_days": len(due_soon),
        "amount_due_in_30_days": round(sum(s.cost for s in due_soon), 2),
    }
