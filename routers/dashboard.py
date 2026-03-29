from collections import defaultdict
from datetime import date, timedelta
from typing import Dict, List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
import models
import schemas

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def _build_upcoming(subs: list, today: date, cutoff: date) -> List[schemas.UpcomingRenewal]:
    result = []
    for s in subs:
        if s.status == "active" and today <= s.renewal_date <= cutoff:
            result.append(schemas.UpcomingRenewal(
                id=s.id,
                tool_name=s.tool_name,
                category=s.category,
                renewal_date=s.renewal_date,
                cost=s.cost,
                currency=s.currency,
                billing_cycle=s.billing_cycle,
                days_until_renewal=(s.renewal_date - today).days,
            ))
    return sorted(result, key=lambda x: x.days_until_renewal)


@router.get("/", response_model=schemas.DashboardOut, summary="Full subscription analytics dashboard")
def get_dashboard(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    all_subs = db.query(models.Subscription).filter(models.Subscription.user_id == current_user.id).all()
    today = date.today()

    # ── Status breakdown ──────────────────────────────────────────────────────
    active = [s for s in all_subs if s.status == "active"]
    inactive = [s for s in all_subs if s.status == "inactive"]
    cancelled = [s for s in all_subs if s.status == "cancelled"]

    # ── Cost calculations (active subs only) ──────────────────────────────────
    monthly_cost = sum(s.cost for s in active if s.billing_cycle == "monthly")
    yearly_cost = sum(s.cost for s in active if s.billing_cycle == "yearly")
    annual_cost = round(monthly_cost * 12 + yearly_cost, 2)
    avg_cost = round(annual_cost / len(active), 2) if active else 0.0

    # ── Renewal windows ───────────────────────────────────────────────────────
    upcoming_7 = _build_upcoming(active, today, today + timedelta(days=7))
    upcoming_30 = _build_upcoming(active, today, today + timedelta(days=30))

    # ── Overdue ───────────────────────────────────────────────────────────────
    overdue = []
    for s in active:
        if s.renewal_date < today:
            overdue.append(schemas.OverdueSubscription(
                id=s.id,
                tool_name=s.tool_name,
                category=s.category,
                renewal_date=s.renewal_date,
                cost=s.cost,
                days_overdue=(today - s.renewal_date).days,
            ))

    # ── Top 5 most expensive (active) ─────────────────────────────────────────
    top5 = sorted(active, key=lambda x: x.cost, reverse=True)[:5]
    top5_out = [
        schemas.SubscriptionOut(
            id=s.id, tool_name=s.tool_name, purchase_date=s.purchase_date,
            billing_cycle=s.billing_cycle, renewal_date=s.renewal_date, cost=s.cost,
            category=s.category, status=s.status, description=s.description,
            currency=s.currency, created_at=s.created_at,
            days_until_renewal=max((s.renewal_date - today).days, 0),
        )
        for s in top5
    ]

    # ── Spend by category ─────────────────────────────────────────────────────
    cat_map: Dict[str, List] = defaultdict(list)
    for s in active:
        cat_map[s.category].append(s)

    spend_by_cat = []
    for cat, items in sorted(cat_map.items()):
        cat_total = round(sum(i.cost for i in items), 2)
        spend_by_cat.append(schemas.CategorySpend(
            category=cat,
            total_cost=cat_total,
            subscription_count=len(items),
            percentage_of_total=round((cat_total / annual_cost * 100), 1) if annual_cost else 0.0,
        ))
    spend_by_cat.sort(key=lambda x: x.total_cost, reverse=True)

    # ── Spend by billing cycle ────────────────────────────────────────────────
    spend_by_cycle = {
        "monthly": round(monthly_cost, 2),
        "yearly": round(yearly_cost, 2),
        "monthly_annualized": round(monthly_cost * 12, 2),
    }

    # ── Recent additions (this calendar month) ────────────────────────────────
    added_this_month = sum(
        1 for s in all_subs
        if s.created_at.year == today.year and s.created_at.month == today.month
    )

    return schemas.DashboardOut(
        total_subscriptions=len(all_subs),
        active_subscriptions=len(active),
        inactive_subscriptions=len(inactive),
        cancelled_subscriptions=len(cancelled),
        total_monthly_cost=round(monthly_cost, 2),
        total_yearly_cost=round(yearly_cost, 2),
        total_annual_cost=annual_cost,
        average_cost_per_subscription=avg_cost,
        upcoming_renewals_7_days=upcoming_7,
        upcoming_renewals_30_days=upcoming_30,
        overdue_subscriptions=sorted(overdue, key=lambda x: x.days_overdue, reverse=True),
        top_5_expensive=top5_out,
        spend_by_category=spend_by_cat,
        spend_by_billing_cycle=spend_by_cycle,
        subscriptions_added_this_month=added_this_month,
    )
