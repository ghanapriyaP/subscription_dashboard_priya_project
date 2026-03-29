"""
scheduler.py
------------
APScheduler background jobs:
  - 7-day renewal reminders  (daily)
  - 30-day renewal reminders (daily)
  - Mock webhook notifications
Email is mocked — all output printed to console/logs.
"""
import logging
from datetime import date, timedelta

from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger(__name__)


# ── Mock notification senders ─────────────────────────────────────────────────

def _mock_email(to: str, subject: str, body: str) -> None:
    logger.info("[EMAIL MOCK] To: %s | Subject: %s", to, subject)
    print(f"\n{'='*60}")
    print(f"[EMAIL NOTIFICATION]")
    print(f"  To      : {to}")
    print(f"  Subject : {subject}")
    print(f"  Body    : {body}")
    print(f"{'='*60}\n")


def _mock_webhook(event: str, payload: dict) -> None:
    logger.info("[WEBHOOK MOCK] Event: %s | Payload: %s", event, payload)
    print(f"\n[WEBHOOK] Event: {event} | Data: {payload}\n")


# ── Job: 7-day reminders ──────────────────────────────────────────────────────

def check_7day_renewals(session_factory) -> None:
    db = session_factory()
    try:
        from models import Subscription, User
        today = date.today()
        cutoff = today + timedelta(days=7)

        subs = (
            db.query(Subscription)
            .filter(
                Subscription.status == "active",
                Subscription.renewal_date >= today,
                Subscription.renewal_date <= cutoff,
            )
            .all()
        )

        for sub in subs:
            user = db.query(User).filter(User.id == sub.user_id).first()
            if not user:
                continue
            days_left = (sub.renewal_date - today).days
            urgency = "⚠️ URGENT — " if days_left <= 2 else ""

            subject = f"{urgency}Subscription Renewal in {days_left} day(s): {sub.tool_name}"
            body = (
                f"Your subscription to {sub.tool_name} ({sub.category}) "
                f"renews on {sub.renewal_date} ({days_left} day(s) away). "
                f"Cost: ${sub.cost:.2f} {sub.currency} ({sub.billing_cycle}). "
                f"Please ensure your payment method is up to date."
            )
            _mock_email(user.email, subject, body)
            _mock_webhook("subscription.renewal_reminder", {
                "user_email": user.email,
                "tool_name": sub.tool_name,
                "renewal_date": str(sub.renewal_date),
                "cost": sub.cost,
                "days_until_renewal": days_left,
            })

        if not subs:
            logger.info("[Scheduler:7d] No renewals in next 7 days.")
    finally:
        db.close()


# ── Job: 30-day reminders ─────────────────────────────────────────────────────

def check_30day_renewals(session_factory) -> None:
    db = session_factory()
    try:
        from models import Subscription, User
        today = date.today()
        window_start = today + timedelta(days=8)    # 8-30 days (7-day handled above)
        window_end = today + timedelta(days=30)

        subs = (
            db.query(Subscription)
            .filter(
                Subscription.status == "active",
                Subscription.renewal_date >= window_start,
                Subscription.renewal_date <= window_end,
            )
            .all()
        )

        for sub in subs:
            user = db.query(User).filter(User.id == sub.user_id).first()
            if not user:
                continue
            days_left = (sub.renewal_date - today).days
            subject = f"Upcoming Renewal in {days_left} days: {sub.tool_name}"
            body = (
                f"Heads up! Your {sub.tool_name} subscription renews on {sub.renewal_date} "
                f"({days_left} days from now). Cost: ${sub.cost:.2f} {sub.currency}."
            )
            _mock_email(user.email, subject, body)

        if not subs:
            logger.info("[Scheduler:30d] No renewals in 8-30 day window.")
    finally:
        db.close()


# ── Job: Overdue alerts ───────────────────────────────────────────────────────

def check_overdue(session_factory) -> None:
    db = session_factory()
    try:
        from models import Subscription, User
        today = date.today()

        overdue = (
            db.query(Subscription)
            .filter(
                Subscription.status == "active",
                Subscription.renewal_date < today,
            )
            .all()
        )

        for sub in overdue:
            user = db.query(User).filter(User.id == sub.user_id).first()
            if not user:
                continue
            days_overdue = (today - sub.renewal_date).days
            subject = f"🚨 OVERDUE: {sub.tool_name} renewal was {days_overdue} day(s) ago"
            body = (
                f"Your {sub.tool_name} subscription renewal date ({sub.renewal_date}) "
                f"has passed {days_overdue} day(s) ago. "
                f"Please renew to avoid service interruption. Cost: ${sub.cost:.2f}."
            )
            _mock_email(user.email, subject, body)
            _mock_webhook("subscription.overdue", {
                "user_email": user.email,
                "tool_name": sub.tool_name,
                "renewal_date": str(sub.renewal_date),
                "days_overdue": days_overdue,
            })

        if not overdue:
            logger.info("[Scheduler:overdue] No overdue subscriptions.")
    finally:
        db.close()


# ── Scheduler startup ─────────────────────────────────────────────────────────

def start_scheduler(session_factory) -> BackgroundScheduler:
    scheduler = BackgroundScheduler()

    scheduler.add_job(check_7day_renewals, "interval", hours=24, args=[session_factory], id="7day_check")
    scheduler.add_job(check_30day_renewals, "interval", hours=24, args=[session_factory], id="30day_check")
    scheduler.add_job(check_overdue, "interval", hours=12, args=[session_factory], id="overdue_check")

    scheduler.start()
    logger.info("[Scheduler] Started. Jobs: 7-day reminders, 30-day reminders, overdue alerts.")

    # Fire all checks immediately on startup for demo visibility
    check_7day_renewals(session_factory)
    check_30day_renewals(session_factory)
    check_overdue(session_factory)

    return scheduler
