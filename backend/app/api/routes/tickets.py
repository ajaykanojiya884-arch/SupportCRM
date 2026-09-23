from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.api.routes.auth import require_authenticated_user
from app.models.note import Note
from app.models.ticket import Ticket
from app.schemas.ticket import TicketCreate, TicketDetail, TicketListItem, TicketListResponse, TicketUpdate, TicketUpdateResponse

router = APIRouter()


def _generate_ticket_id(db: Session) -> str:
    result = db.execute(select(func.max(Ticket.id))).scalar()
    next_number = (result or 0) + 1
    return f"TKT-{next_number:03d}"


@router.post("/tickets", status_code=201)
async def create_ticket(payload: TicketCreate, db: Session = Depends(get_db), _: object = Depends(require_authenticated_user)) -> dict:
    now = datetime.now(timezone.utc)
    ticket = Ticket(
        ticket_id=_generate_ticket_id(db),
        customer_name=payload.customer_name.strip(),
        customer_email=payload.customer_email.lower().strip(),
        subject=payload.subject.strip(),
        description=payload.description.strip(),
        status="Open",
        created_at=now,
        updated_at=now,
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return {"ticket_id": ticket.ticket_id, "created_at": ticket.created_at.isoformat()}


@router.get("/tickets", response_model=TicketListResponse)
async def list_tickets(
    search: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: object = Depends(require_authenticated_user),
) -> TicketListResponse:
    query = select(Ticket)
    if search and search.strip():
        s = f"%{search.strip()}%"
        query = query.where(
            or_(
                Ticket.ticket_id.ilike(s),
                Ticket.customer_name.ilike(s),
                Ticket.customer_email.ilike(s),
                Ticket.subject.ilike(s),
                Ticket.description.ilike(s),
            )
        )
    if status and status != "All":
        query = query.where(Ticket.status == status)

    total = db.scalar(select(func.count()).select_from(query.subquery()))
    query = query.order_by(Ticket.updated_at.desc(), Ticket.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    rows = db.execute(query).scalars().all()

    items = [
        TicketListItem(
            ticket_id=row.ticket_id,
            customer_name=row.customer_name,
            customer_email=row.customer_email,
            subject=row.subject,
            status=row.status,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
        for row in rows
    ]
    total_pages = (total + page_size - 1) // page_size if total else 0
    return TicketListResponse(items=items, total=total or 0, page=page, page_size=page_size, total_pages=total_pages)


@router.get("/tickets/{ticket_id}", response_model=TicketDetail)
async def get_ticket(ticket_id: str, db: Session = Depends(get_db), _: object = Depends(require_authenticated_user)) -> TicketDetail:
    ticket = db.scalar(select(Ticket).where(Ticket.ticket_id == ticket_id))
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found.")

    note_rows = [
        {"id": note.id, "note_text": note.note_text, "created_at": note.created_at.isoformat()}
        for note in sorted(ticket.notes, key=lambda n: n.created_at, reverse=True)
    ]

    return TicketDetail(
        ticket_id=ticket.ticket_id,
        customer_name=ticket.customer_name,
        customer_email=ticket.customer_email,
        subject=ticket.subject,
        description=ticket.description,
        status=ticket.status,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        notes=note_rows,
    )


@router.put("/tickets/{ticket_id}", response_model=TicketUpdateResponse)
async def update_ticket(ticket_id: str, payload: TicketUpdate, db: Session = Depends(get_db), _: object = Depends(require_authenticated_user)) -> TicketUpdateResponse:
    ticket = db.scalar(select(Ticket).where(Ticket.ticket_id == ticket_id))
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found.")

    if payload.status:
        ticket.status = payload.status
    if payload.notes and payload.notes.strip():
        db.add(Note(ticket_id=ticket.id, note_text=payload.notes.strip(), created_at=datetime.now(timezone.utc)))

    ticket.updated_at = datetime.now(timezone.utc)
    db.commit()
    return TicketUpdateResponse(success=True, updated_at=ticket.updated_at, ticket_id=ticket.ticket_id)
