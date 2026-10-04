from __future__ import annotations

from functools import lru_cache

import jwt
from fastapi import Depends, Header, HTTPException
from jwt.exceptions import PyJWKClientConnectionError, PyJWKClientError
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.session import get_db
from app.models.entities import AuthIdentity, User


@lru_cache(maxsize=4)
def _jwks_client(url: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(url)


def verify_access_token(token: str) -> dict:
    settings = get_settings()
    issuer = getattr(settings, "neon_auth_issuer", "") or getattr(settings, "neon_auth_base_url", "")
    if not issuer or not settings.neon_auth_jwks_url:
        raise HTTPException(status_code=503, detail="Authentication is not configured.")

    try:
        header = jwt.get_unverified_header(token)
        algorithm = header.get("alg")
        if algorithm not in {"RS256", "ES256", "EdDSA"}:
            raise HTTPException(status_code=401, detail="Invalid access token.")
        signing_key = _jwks_client(settings.neon_auth_jwks_url).get_signing_key_from_jwt(token).key
        return jwt.decode(
            token,
            signing_key,
            algorithms=[algorithm],
            audience=settings.neon_auth_audience,
            issuer=issuer,
            options={"require": ["exp", "iss", "sub", "aud"]},
        )
    except PyJWKClientConnectionError as exc:
        raise HTTPException(status_code=503, detail="Authentication provider is unavailable.") from exc
    except (PyJWKClientError, jwt.InvalidTokenError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Invalid access token.") from exc


def _email_set(value: str) -> set[str]:
    return {email.strip().lower() for email in value.split(",") if email.strip()}


def _role_for_claims(claims: dict) -> str:
    email = str(claims.get("email") or "").strip().lower()
    if not email or claims.get("email_verified") is not True:
        return "student"
    settings = get_settings()
    if email in _email_set(settings.neon_auth_admin_emails):
        return "admin"
    if email in _email_set(settings.neon_auth_teacher_emails):
        return "teacher"
    return "student"


def user_for_claims(claims: dict, db: Session) -> dict:
    subject = claims.get("sub")
    if not isinstance(subject, str) or not subject.strip():
        raise HTTPException(status_code=401, detail="Access token has no subject.")

    identity = db.query(AuthIdentity).filter_by(subject=subject).one_or_none()
    user = db.get(User, identity.user_id) if identity else None
    email_claim = claims.get("email")
    email_verified = claims.get("email_verified") is True
    email = str(email_claim).strip().lower() if email_claim and email_verified else None

    if user is None and email:
        user = db.query(User).filter(func.lower(User.email) == email).one_or_none()

    name = str(claims.get("name") or (email.split("@", 1)[0] if email else "Learner"))[:120]
    if user is None:
        user = User(name=name, email=email, role=_role_for_claims(claims))
        db.add(user)
        db.flush()
    else:
        user.name = name
        if email:
            user.email = email
        user.role = _role_for_claims(claims)

    if identity is None:
        db.add(AuthIdentity(subject=subject, user_id=user.id))
    db.commit()
    db.refresh(user)
    return {"id": user.id, "name": user.name, "email": user.email or "", "role": user.role}


def get_current_user_from_headers(
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=401,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    claims = verify_access_token(authorization[7:].strip())
    return user_for_claims(claims, db)


def require_role(required_roles: list[str], user: dict | None) -> dict:
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required.")
    role = (user.get("role") or "student").lower()
    if role not in {item.lower() for item in required_roles} and role != "admin":
        raise HTTPException(status_code=403, detail=f"Access denied. Required role: {', '.join(required_roles)}")
    return user
