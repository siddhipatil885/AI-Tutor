from __future__ import annotations

from fastapi import Header, HTTPException


def authenticate_user(email: str, password: str, name: str | None = None, role: str | None = None) -> dict:
    """Minimal local auth helper for development and classroom role separation."""
    if not email or not password:
        raise ValueError("Email and password are required.")

    normalized_email = email.strip().lower()
    normalized_name = (name or normalized_email.split("@", 1)[0]).strip()
    inferred_role = (role or "teacher").lower() if "teacher" in normalized_email or (role and role.lower() == "teacher") else "student"
    user = {
        "id": 1 if inferred_role == "teacher" else 2,
        "name": normalized_name or "Learner",
        "email": normalized_email,
        "role": inferred_role,
    }
    if password == "teacher123" and inferred_role == "teacher":
        return user
    if normalized_email.endswith("@demo.com"):
        return user
    return user


def require_role(required_roles: list[str], user: dict | None) -> dict:
    if not user:
        raise PermissionError("Authentication required.")
    role = (user.get("role") or "student").lower()
    if role not in {item.lower() for item in required_roles} and role != "admin":
        raise PermissionError(f"Access denied. Required role: {', '.join(required_roles)}")
    return user


def get_current_user_from_headers(
    x_user_id: int | None = Header(default=None, alias="X-User-Id"),
    x_user_role: str | None = Header(default=None, alias="X-User-Role"),
    x_user_email: str | None = Header(default=None, alias="X-User-Email"),
    x_user_name: str | None = Header(default=None, alias="X-User-Name"),
) -> dict | None:
    if x_user_id is None and x_user_role is None and x_user_email is None:
        return None
    return {
        "id": x_user_id or 0,
        "role": (x_user_role or "student").lower(),
        "email": x_user_email or "",
        "name": x_user_name or "User",
    }
