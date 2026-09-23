from __future__ import annotations

import hashlib
import secrets
import smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import EmailStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.models.auth import Session as AuthSession, User, VerificationCode
from app.schemas.auth import AuthRequest, AuthVerifyRequest, AuthenticatedUser, SessionResponse

router = APIRouter()
security = HTTPBearer(auto_error=False)


def _hash_value(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _generate_otp() -> str:
    return str(secrets.randbelow(900000) + 100000)


def _masked_email(email: str) -> str:
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        return f"{local[:1]}***@{domain}"
    return f"{local[:2]}***@{domain}"


def _send_otp_email(to_email: str, otp: str) -> None:
    smtp_user = settings.smtp_user.strip()
    smtp_password = settings.smtp_password.strip().replace(" ", "")
    if not smtp_user or not smtp_password:
        raise RuntimeError("SMTP user and password are not configured.")

    message = EmailMessage()
    message["Subject"] = "Your Datastraw verification code"
    message["From"] = smtp_user
    message["To"] = to_email
    message.set_content(
        f"Your Datastraw verification code is: {otp}\n\n"
        f"This code will expire in {settings.otp_expiration_minutes} minutes.\n\n"
        "Use this code to continue login."
    )

    smtp_host = (settings.smtp_host or "").strip()
    if not smtp_host:
        raise RuntimeError("SMTP host is not configured.")

    with smtplib.SMTP(smtp_host, settings.smtp_port, timeout=50) as server:
        if settings.smtp_port == 465:
            server.starttls()
        elif smtp_host.lower() not in {"localhost", "127.0.0.1", "0.0.0.0"}:
            server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(message)


def _normalize_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


@router.post("/request-otp")
async def request_otp(payload: AuthRequest, db: Session = Depends(get_db)) -> dict:
    email = str(payload.email).lower().strip()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Invalid email address.")

    otp = _generate_otp()
    otp_hash = _hash_value(otp)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.otp_expiration_minutes)
    cooldown = datetime.now(timezone.utc) - timedelta(seconds=settings.otp_resend_cooldown_seconds)

    existing = db.scalar(
        select(VerificationCode).where(VerificationCode.email == email).order_by(VerificationCode.created_at.desc())
    )
    if existing:
        existing_created_at = _normalize_datetime(existing.created_at)
        if existing_created_at and existing_created_at > cooldown:
            seconds_left = max(0, settings.otp_resend_cooldown_seconds - int((datetime.now(timezone.utc) - existing_created_at).total_seconds()))
            raise HTTPException(status_code=429, detail=f"Please wait {max(seconds_left, 1)} seconds before requesting a new code.")

    db.add(
        VerificationCode(
            email=email,
            code_hash=otp_hash,
            expires_at=expires_at,
            attempts=0,
            created_at=datetime.now(timezone.utc),
            is_active=True,
        )
    )
    db.commit()

    response = {"message": "Verification code sent.", "masked_email": _masked_email(email)}
    smtp_host = (settings.smtp_host or "").strip().lower()
    smtp_configured = bool(
        settings.smtp_user.strip()
        and settings.smtp_password.strip()
        and smtp_host
        and smtp_host not in {"localhost", "127.0.0.1", "0.0.0.0"}
    )

    if smtp_configured:
        try:
            _send_otp_email(email, otp)
        except (OSError, smtplib.SMTPException, RuntimeError) as exc:
            existing_code = db.scalar(
                select(VerificationCode)
                .where(VerificationCode.email == email)
                .where(VerificationCode.code_hash == otp_hash)
            )
            if existing_code:
                existing_code.is_active = False
                db.commit()
            raise HTTPException(status_code=500, detail="Unable to send verification email. Check SMTP credentials and Gmail app password configuration.") from exc
        return response

    if settings.environment.lower() == "development" or smtp_host in {"localhost", "127.0.0.1", "0.0.0.0"}:
        response["otp"] = otp
    return response


@router.post("/verify-otp", response_model=SessionResponse)
async def verify_otp(payload: AuthVerifyRequest, db: Session = Depends(get_db)) -> SessionResponse:
    email = str(payload.email).lower().strip()
    code = payload.code.strip()
    now = datetime.now(timezone.utc)

    existing = db.scalar(
        select(VerificationCode)
        .where(VerificationCode.email == email)
        .where(VerificationCode.is_active.is_(True))
        .order_by(VerificationCode.created_at.desc())
    )
    if not existing:
        raise HTTPException(status_code=400, detail="Invalid or expired verification code.")

    expires_at = _normalize_datetime(existing.expires_at) or now
    if expires_at < now:
        existing.is_active = False
        db.commit()
        raise HTTPException(status_code=400, detail="Verification code has expired.")

    if existing.attempts >= settings.max_otp_attempts:
        existing.is_active = False
        db.commit()
        raise HTTPException(status_code=400, detail="Too many failed attempts. Request a new code.")

    if _hash_value(code) != existing.code_hash:
        existing.attempts += 1
        db.commit()
        raise HTTPException(status_code=400, detail="Invalid verification code.")

    existing.used_at = now
    existing.is_active = False

    user = db.scalar(select(User).where(User.email == email))
    if not user:
        user = User(email=email, created_at=now)
        db.add(user)

    session_token = secrets.token_urlsafe(32)
    session_expires = now + timedelta(minutes=settings.session_expiration_minutes)
    db.add(
        AuthSession(
            email=email,
            token_hash=_hash_value(session_token),
            expires_at=session_expires,
            created_at=now,
            is_active=True,
        )
    )

    db.commit()
    return SessionResponse(token=session_token, expires_at=session_expires)


@router.get("/me")
async def get_me(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)) -> AuthenticatedUser:
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required.")

    token_hash = _hash_value(credentials.credentials)
    session = db.scalar(
        select(AuthSession)
        .where(AuthSession.token_hash == token_hash)
        .where(AuthSession.is_active.is_(True))
        .order_by(AuthSession.created_at.desc())
    )
    if not session:
        raise HTTPException(status_code=401, detail="Session expired.")

    expires_at = _normalize_datetime(session.expires_at)
    if expires_at is None or expires_at <= datetime.now(timezone.utc):
        session.is_active = False
        db.commit()
        raise HTTPException(status_code=401, detail="Session expired.")

    return AuthenticatedUser(email=session.email)


@router.post("/logout")
async def logout(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)) -> dict:
    if not credentials:
        return {"message": "Logged out."}

    token_hash = _hash_value(credentials.credentials)
    session = db.scalar(select(AuthSession).where(AuthSession.token_hash == token_hash))
    if session:
        session.is_active = False
        db.commit()
    return {"message": "Logged out."}


def require_authenticated_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> AuthenticatedUser:
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required.")

    token_hash = _hash_value(credentials.credentials)
    session = db.scalar(
        select(AuthSession)
        .where(AuthSession.token_hash == token_hash)
        .where(AuthSession.is_active.is_(True))
        .order_by(AuthSession.created_at.desc())
    )
    if not session:
        raise HTTPException(status_code=401, detail="Session expired.")

    expires_at = _normalize_datetime(session.expires_at)
    if expires_at is None or expires_at <= datetime.now(timezone.utc):
        session.is_active = False
        db.commit()
        raise HTTPException(status_code=401, detail="Session expired.")

    return AuthenticatedUser(email=session.email)
