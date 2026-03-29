from datetime import date, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from auth import get_current_user
from database import get_db
import models
import schemas

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])


@router.get("/", response_model=List[schemas.SubscriptionOut], summary="List subscriptions with optional filters")
def list_subscriptions(
    # Filters
    status: Optional[str] = Query(None, description="Filter by status: active | inactive | cancelled"),
    category: Optional[str] = Query(None, description="Filter by category"),
    billing_cycle: Optional[str] = Query(None, description="Filter by billing_cycle: monthly | yearly"),
    search: Optional[str] = Query(None, description="Search by tool name (case-insensitive)"),
    renewing_in_days: Optional[int] = Query(None, description="Only subscriptions renewing within N days"),
    # Sorting
    sort_by: str = Query("created_at", description="Sort by: cost | renewal_date | tool_name | created_at"),
    sort_order: str = Query("desc", description="asc or desc"),
    # Pagination
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    query = db.query(models.Subscription).filter(models.Subscription.user_id == current_user.id)

    if status:
        query = query.filter(models.Subscription.status == status)
    if category:
        query = query.filter(models.Subscription.category == category)
    if billing_cycle:
        query = query.filter(models.Subscription.billing_cycle == billing_cycle)
    if search:
        query = query.filter(models.Subscription.tool_name.ilike(f"%{search}%"))
    if renewing_in_days is not None and isinstance(renewing_in_days, int):
        today_filter = date.today()
        cutoff = today_filter + timedelta(days=renewing_in_days)
        query = query.filter(models.Subscription.renewal_date >= today_filter, models.Subscription.renewal_date <= cutoff)

    # Sorting
    sort_col = getattr(models.Subscription, sort_by, models.Subscription.created_at)
    if sort_order == "asc":
        query = query.order_by(sort_col.asc())
    else:
        query = query.order_by(sort_col.desc())

    # Pagination
    total = query.count()
    subs = query.offset((page - 1) * page_size).limit(page_size).all()

    today = date.today()
    return [
        schemas.SubscriptionOut(
            id=s.id, tool_name=s.tool_name, purchase_date=s.purchase_date,
            billing_cycle=s.billing_cycle, renewal_date=s.renewal_date, cost=s.cost,
            category=s.category, status=s.status, description=s.description,
            currency=s.currency, created_at=s.created_at,
            days_until_renewal=(s.renewal_date - today).days,
        )
        for s in subs
    ]


@router.get("/{sub_id}", response_model=schemas.SubscriptionOut, summary="Get a single subscription")
def get_subscription(
    sub_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    s = db.query(models.Subscription).filter(
        models.Subscription.id == sub_id,
        models.Subscription.user_id == current_user.id,
    ).first()
    if not s:
        raise HTTPException(status_code=404, detail="Subscription not found")
    today = date.today()
    return schemas.SubscriptionOut(
        id=s.id, tool_name=s.tool_name, purchase_date=s.purchase_date,
        billing_cycle=s.billing_cycle, renewal_date=s.renewal_date, cost=s.cost,
        category=s.category, status=s.status, description=s.description,
        currency=s.currency, created_at=s.created_at,
        days_until_renewal=(s.renewal_date - today).days,
    )


@router.post("/", response_model=schemas.SubscriptionOut, status_code=status.HTTP_201_CREATED, summary="Add a new subscription")
def create_subscription(
    payload: schemas.SubscriptionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    sub = models.Subscription(**payload.model_dump(), user_id=current_user.id)
    db.add(sub)
    db.commit()
    db.refresh(sub)
    today = date.today()
    return schemas.SubscriptionOut(
        id=sub.id, tool_name=sub.tool_name, purchase_date=sub.purchase_date,
        billing_cycle=sub.billing_cycle, renewal_date=sub.renewal_date, cost=sub.cost,
        category=sub.category, status=sub.status, description=sub.description,
        currency=sub.currency, created_at=sub.created_at,
        days_until_renewal=(sub.renewal_date - today).days,
    )


@router.put("/{sub_id}", response_model=schemas.SubscriptionOut, summary="Update a subscription")
def update_subscription(
    sub_id: int,
    payload: schemas.SubscriptionUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    sub = db.query(models.Subscription).filter(
        models.Subscription.id == sub_id,
        models.Subscription.user_id == current_user.id,
    ).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(sub, field, value)
    db.commit()
    db.refresh(sub)
    today = date.today()
    return schemas.SubscriptionOut(
        id=sub.id, tool_name=sub.tool_name, purchase_date=sub.purchase_date,
        billing_cycle=sub.billing_cycle, renewal_date=sub.renewal_date, cost=sub.cost,
        category=sub.category, status=sub.status, description=sub.description,
        currency=sub.currency, created_at=sub.created_at,
        days_until_renewal=(sub.renewal_date - today).days,
    )


@router.delete("/{sub_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a subscription")
def delete_subscription(
    sub_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    sub = db.query(models.Subscription).filter(
        models.Subscription.id == sub_id,
        models.Subscription.user_id == current_user.id,
    ).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    db.delete(sub)
    db.commit()
