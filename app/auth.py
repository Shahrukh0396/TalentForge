import logging
from datetime import datetime, timezone

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient, decode
from jwt.exceptions import PyJWTError
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.db import get_engine
from app.models.user import User

logger = logging.getLogger(__name__)

_bearer = HTTPBearer(auto_error=False)
_jwks_clients: dict[str, PyJWKClient] = {}


def _jwks(version: str) -> PyJWKClient:
    if not settings.entra_tenant_id or not settings.api_client_id:
        raise HTTPException(status_code=500, detail="Authentication is not configured")
    client = _jwks_clients.get(version)
    if client is None:
        tenant = settings.entra_tenant_id
        if version == "1.0":
            url = f"https://login.microsoftonline.com/{tenant}/discovery/keys"
        else:
            url = f"https://login.microsoftonline.com/{tenant}/discovery/v2.0/keys"
        client = PyJWKClient(url, cache_keys=True)
        _jwks_clients[version] = client
    return client


def _token_version(token: str) -> str:
    try:
        unverified = decode(token, options={"verify_signature": False})
    except PyJWTError:
        raise _unauthorized()
    issuer = unverified.get("iss")
    if unverified.get("ver") == "1.0" or (
        isinstance(issuer, str) and issuer.startswith("https://sts.windows.net/")
    ):
        return "1.0"
    return "2.0"


def _expected_issuer(version: str) -> str:
    tenant = settings.entra_tenant_id
    if version == "1.0":
        return f"https://sts.windows.net/{tenant}/"
    return f"https://login.microsoftonline.com/{tenant}/v2.0"


def _unauthorized() -> HTTPException:
    return HTTPException(status_code=401, detail="Invalid or expired token")


def _forbidden() -> HTTPException:
    return HTTPException(status_code=403, detail="Access denied")


def _claims_from_token(token: str) -> dict:
    version = _token_version(token)
    try:
        signing_key = _jwks(version).get_signing_key_from_jwt(token)
        return decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=[settings.api_client_id, f"api://{settings.api_client_id}"],
            issuer=_expected_issuer(version),
            options={"require": ["exp", "iat", "iss", "aud"]},
        )
    except HTTPException:
        raise
    except PyJWTError as exc:
        logger.warning("Rejected access token: %s", exc)
        raise _unauthorized()
    except Exception as exc:
        logger.warning("Rejected access token: %s", exc.__class__.__name__)
        raise _unauthorized()


def _identity(claims: dict) -> dict:
    tid = claims.get("tid")
    oid = claims.get("oid")
    if not isinstance(tid, str) or not isinstance(oid, str) or not tid or not oid:
        raise _unauthorized()
    if tid != settings.entra_tenant_id:
        raise _forbidden()

    scope = claims.get("scp")
    scopes = scope.split() if isinstance(scope, str) else []
    if "access_as_user" not in scopes:
        raise _forbidden()

    roles = claims.get("roles", [])
    if isinstance(roles, str):
        roles = [roles]
    if not isinstance(roles, list):
        roles = []

    return {
        "tid": tid,
        "oid": oid,
        "name": claims.get("name") if isinstance(claims.get("name"), str) else None,
        "preferred_username": claims.get("preferred_username")
        if isinstance(claims.get("preferred_username"), str)
        else None,
        "roles": [role for role in roles if isinstance(role, str)],
    }


def _upsert_user(db: Session, user: dict) -> None:
    now = datetime.now(timezone.utc)
    stmt = insert(User).values(
        tid=user["tid"],
        oid=user["oid"],
        name=user["name"],
        preferred_username=user["preferred_username"],
        created_at=now,
        updated_at=now,
    ).on_conflict_do_update(
        constraint="uq_users_tid_oid",
        set_={
            "name": user["name"],
            "preferred_username": user["preferred_username"],
            "updated_at": now,
        },
    )
    db.execute(stmt)
    db.commit()


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict:
    if credentials is None or credentials.scheme.lower() != "bearer" or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Authentication required")

    user = _identity(_claims_from_token(credentials.credentials))
    db: Session = sessionmaker(bind=get_engine())()
    try:
        _upsert_user(db, user)
    finally:
        db.close()
    return user


def require_role(role: str):
    def _require(user: dict = Depends(current_user)) -> dict:
        if role not in user.get("roles", []):
            raise _forbidden()
        return user

    return _require
