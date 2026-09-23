from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.routes.auth import require_authenticated_user
from app.db.database import get_db
from app.models.ticket import Ticket

router = APIRouter()


def _normalize_status(value: str) -> str:
    return value if value in {"Open", "In Progress", "Closed"} else "Open"


@router.get("/overview")
async def overview(db: Session = Depends(get_db), _: object = Depends(require_authenticated_user)) -> dict:
    total = db.scalar(select(func.count(Ticket.id))) or 0
    open_count = db.scalar(select(func.count(Ticket.id)).where(Ticket.status == "Open")) or 0
    progress_count = db.scalar(select(func.count(Ticket.id)).where(Ticket.status == "In Progress")) or 0
    closed_count = db.scalar(select(func.count(Ticket.id)).where(Ticket.status == "Closed")) or 0
    created_last_7 = db.scalar(
        select(func.count(Ticket.id)).where(Ticket.created_at >= datetime.now(timezone.utc) - timedelta(days=7))
    ) or 0
    closed_last_7 = db.scalar(
        select(func.count(Ticket.id)).where(Ticket.updated_at >= datetime.now(timezone.utc) - timedelta(days=7), Ticket.status == "Closed")
    ) or 0

    return {
        "total_tickets": total,
        "open": open_count,
        "in_progress": progress_count,
        "closed": closed_count,
        "created_last_7_days": created_last_7,
        "closed_last_7_days": closed_last_7,
        "status_distribution": {
            "Open": open_count,
            "In Progress": progress_count,
            "Closed": closed_count,
        },
    }


@router.get("/trends")
async def trends(db: Session = Depends(get_db), _: object = Depends(require_authenticated_user)) -> dict:
    days = []
    today = datetime.now(timezone.utc).date()
    for i in range(7):
        day = today - timedelta(days=6 - i)
        day_start = datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc)
        next_day = day_start + timedelta(days=1)
        created_count = db.scalar(
            select(func.count(Ticket.id)).where(Ticket.created_at >= day_start, Ticket.created_at < next_day)
        ) or 0
        closed_count = db.scalar(
            select(func.count(Ticket.id)).where(Ticket.updated_at >= day_start, Ticket.updated_at < next_day, Ticket.status == "Closed")
        ) or 0
        days.append({"date": day.isoformat(), "created": created_count, "closed": closed_count})

    return {"daily": days}
