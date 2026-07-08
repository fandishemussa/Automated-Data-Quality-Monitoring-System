"""Database-backed user management for the enterprise dashboard."""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from config.settings import get_env
from data_sources.postgres_connector import create_monitor_engine
from utils.logger import get_logger


logger = get_logger(__name__)

ALLOWED_ROLES = {"admin", "analyst", "data_analyst", "data_engineer", "viewer"}
DEFAULT_ROLE = "viewer"

CREATE_USERS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS data_quality_users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name VARCHAR(255),
    email VARCHAR(255),
    job_title VARCHAR(255),
    department VARCHAR(255),
    phone_number VARCHAR(100),
    role VARCHAR(50) DEFAULT 'viewer',
    is_active BOOLEAN DEFAULT TRUE,
    created_by VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP
)
"""

ALTER_USERS_TABLE_SQL = [
    "ALTER TABLE IF EXISTS data_quality_users ADD COLUMN IF NOT EXISTS password_hash TEXT",
    "ALTER TABLE IF EXISTS data_quality_users ADD COLUMN IF NOT EXISTS full_name VARCHAR(255)",
    "ALTER TABLE IF EXISTS data_quality_users ADD COLUMN IF NOT EXISTS email VARCHAR(255)",
    "ALTER TABLE IF EXISTS data_quality_users ADD COLUMN IF NOT EXISTS job_title VARCHAR(255)",
    "ALTER TABLE IF EXISTS data_quality_users ADD COLUMN IF NOT EXISTS department VARCHAR(255)",
    "ALTER TABLE IF EXISTS data_quality_users ADD COLUMN IF NOT EXISTS phone_number VARCHAR(100)",
    "ALTER TABLE IF EXISTS data_quality_users ADD COLUMN IF NOT EXISTS role VARCHAR(50) DEFAULT 'viewer'",
    "ALTER TABLE IF EXISTS data_quality_users ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE",
    "ALTER TABLE IF EXISTS data_quality_users ADD COLUMN IF NOT EXISTS created_by VARCHAR(255)",
    "ALTER TABLE IF EXISTS data_quality_users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    "ALTER TABLE IF EXISTS data_quality_users ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMP",
]

CREATE_PROFILE_UPDATES_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS data_quality_user_profile_updates (
    id SERIAL PRIMARY KEY,
    user_id INT,
    username VARCHAR(100),
    requested_changes TEXT,
    status VARCHAR(20) DEFAULT 'PENDING',
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reviewed_by VARCHAR(255),
    reviewed_at TIMESTAMP,
    review_notes TEXT
)
"""

ALTER_PROFILE_UPDATES_TABLE_SQL = [
    "ALTER TABLE IF EXISTS data_quality_user_profile_updates ADD COLUMN IF NOT EXISTS requested_changes TEXT",
    "ALTER TABLE IF EXISTS data_quality_user_profile_updates ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'PENDING'",
    "ALTER TABLE IF EXISTS data_quality_user_profile_updates ADD COLUMN IF NOT EXISTS reviewed_by VARCHAR(255)",
    "ALTER TABLE IF EXISTS data_quality_user_profile_updates ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMP",
    "ALTER TABLE IF EXISTS data_quality_user_profile_updates ADD COLUMN IF NOT EXISTS review_notes TEXT",
]

PROFILE_FIELDS = ("full_name", "email", "job_title", "department", "phone_number")


def ensure_users_table() -> None:
    """Create or update the dashboard users table if needed."""

    engine = create_monitor_engine()
    with engine.begin() as connection:
        connection.execute(text(CREATE_USERS_TABLE_SQL))
        for statement in ALTER_USERS_TABLE_SQL:
            connection.execute(text(statement))
        connection.execute(text(CREATE_PROFILE_UPDATES_TABLE_SQL))
        for statement in ALTER_PROFILE_UPDATES_TABLE_SQL:
            connection.execute(text(statement))


def ensure_default_admin() -> None:
    """Create the bootstrap admin user when no users exist yet."""

    ensure_users_table()
    engine = create_monitor_engine()
    username = str(get_env("DASHBOARD_USERNAME", "admin") or "admin")
    password = str(get_env("DASHBOARD_PASSWORD", "change_me") or "change_me")

    with engine.begin() as connection:
        user_count = connection.execute(text("SELECT COUNT(*) FROM data_quality_users")).scalar_one()
        if int(user_count) > 0:
            return

        connection.execute(
            text(
                """
                INSERT INTO data_quality_users (
                    username, password_hash, full_name, email, role, is_active, created_by
                )
                VALUES (
                    :username, :password_hash, :full_name, :email, 'admin', TRUE, 'system'
                )
                """
            ),
            {
                "username": username,
                "password_hash": hash_password(password),
                "full_name": "Default Admin",
                "email": "",
            },
        )
    logger.info("Created bootstrap admin user: %s", username)


def hash_password(password: str) -> str:
    """Hash a password with PBKDF2-HMAC-SHA256."""

    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("ascii"), 120_000)
    return f"pbkdf2_sha256$120000${salt}${digest.hex()}"


def verify_password(password: str, stored_hash: str | None) -> bool:
    """Verify a password against a stored PBKDF2 hash."""

    if not stored_hash:
        return False

    try:
        algorithm, iterations, salt, digest = stored_hash.split("$", 3)
    except ValueError:
        return False

    if algorithm != "pbkdf2_sha256":
        return False

    candidate = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("ascii"),
        int(iterations),
    ).hex()
    return hmac.compare_digest(candidate, digest)


def authenticate_user(username: str, password: str) -> dict[str, Any] | None:
    """Authenticate an active user and update their last login timestamp."""

    ensure_default_admin()
    engine = create_monitor_engine()
    with engine.begin() as connection:
        row = connection.execute(
            text("SELECT * FROM data_quality_users WHERE username = :username"),
            {"username": username},
        ).mappings().first()

        if row is None or not row.get("is_active"):
            return None

        user = dict(row)
        if not verify_password(password, user.get("password_hash")):
            return None

        connection.execute(
            text(
                """
                UPDATE data_quality_users
                SET last_login_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                WHERE id = :user_id
                """
            ),
            {"user_id": user["id"]},
        )

    return _public_user(user)


def list_users() -> list[dict[str, Any]]:
    """Return all dashboard users without password hashes."""

    ensure_default_admin()
    engine = create_monitor_engine()
    with engine.begin() as connection:
        rows = connection.execute(
            text(
                """
                SELECT id, username, full_name, email, job_title, department, phone_number,
                       role, is_active, created_by,
                       created_at, updated_at, last_login_at
                FROM data_quality_users
                ORDER BY username ASC
                """
            )
        ).mappings().all()
    return [_with_profile_completion(dict(row)) for row in rows]


def create_user(payload: dict[str, Any], created_by: str) -> dict[str, Any]:
    """Create a dashboard user."""

    ensure_default_admin()
    username = _required_string(payload, "username")
    password = _required_string(payload, "password")
    role = _normalize_role(payload.get("role"))

    try:
        engine = create_monitor_engine()
        with engine.begin() as connection:
            row = connection.execute(
                text(
                    """
                    INSERT INTO data_quality_users (
                        username, password_hash, full_name, email, job_title, department,
                        phone_number, role, is_active, created_by
                    )
                    VALUES (
                        :username, :password_hash, :full_name, :email, :job_title, :department,
                        :phone_number, :role, :is_active, :created_by
                    )
                    RETURNING id, username, full_name, email, job_title, department, phone_number,
                              role, is_active, created_by,
                              created_at, updated_at, last_login_at
                    """
                ),
                {
                    "username": username,
                    "password_hash": hash_password(password),
                    "full_name": _clean_optional(payload.get("full_name")),
                    "email": _clean_optional(payload.get("email")),
                    "job_title": _clean_optional(payload.get("job_title")),
                    "department": _clean_optional(payload.get("department")),
                    "phone_number": _clean_optional(payload.get("phone_number")),
                    "role": role,
                    "is_active": bool(payload.get("is_active", True)),
                    "created_by": created_by,
                },
            ).mappings().one()
    except IntegrityError as exc:
        raise ValueError(f"User '{username}' already exists.") from exc
    except SQLAlchemyError as exc:
        logger.exception("User creation failed.")
        raise RuntimeError("Unable to create user. Check backend logs.") from exc

    return _with_profile_completion(dict(row))


def update_user(user_id: int, payload: dict[str, Any], updated_by: str) -> dict[str, Any]:
    """Update an existing dashboard user."""

    ensure_default_admin()
    allowed_fields: dict[str, Any] = {}

    for field in PROFILE_FIELDS:
        if field in payload:
            allowed_fields[field] = _clean_optional(payload.get(field))
    if "role" in payload:
        allowed_fields["role"] = _normalize_role(payload.get("role"))
    if "is_active" in payload:
        allowed_fields["is_active"] = bool(payload.get("is_active"))
    if payload.get("password"):
        allowed_fields["password_hash"] = hash_password(str(payload["password"]))

    if not allowed_fields:
        return get_user(user_id)

    assignments = [f"{field} = :{field}" for field in allowed_fields]
    assignments.append("updated_at = CURRENT_TIMESTAMP")
    params = {**allowed_fields, "user_id": user_id, "updated_by": updated_by}

    engine = create_monitor_engine()
    with engine.begin() as connection:
        row = connection.execute(
            text(
                f"""
                UPDATE data_quality_users
                SET {", ".join(assignments)}
                WHERE id = :user_id
                RETURNING id, username, full_name, email, job_title, department, phone_number,
                          role, is_active, created_by,
                          created_at, updated_at, last_login_at
                """
            ),
            params,
        ).mappings().first()

    if row is None:
        raise ValueError("User not found.")
    return _with_profile_completion(dict(row))


def deactivate_user(user_id: int, updated_by: str) -> dict[str, Any]:
    """Deactivate a dashboard user."""

    return update_user(user_id, {"is_active": False}, updated_by)


def get_user(user_id: int) -> dict[str, Any]:
    """Return one dashboard user by id."""

    ensure_default_admin()
    engine = create_monitor_engine()
    with engine.begin() as connection:
        row = connection.execute(
            text(
                """
                SELECT id, username, full_name, email, job_title, department, phone_number,
                       role, is_active, created_by,
                       created_at, updated_at, last_login_at
                FROM data_quality_users
                WHERE id = :user_id
                """
            ),
            {"user_id": user_id},
        ).mappings().first()
    if row is None:
        raise ValueError("User not found.")
    return _with_profile_completion(dict(row))


def get_user_by_username(username: str) -> dict[str, Any]:
    """Return one dashboard user by username."""

    ensure_default_admin()
    engine = create_monitor_engine()
    with engine.begin() as connection:
        row = connection.execute(
            text(
                """
                SELECT id, username, full_name, email, job_title, department, phone_number,
                       role, is_active, created_by, created_at, updated_at, last_login_at
                FROM data_quality_users
                WHERE username = :username
                """
            ),
            {"username": username},
        ).mappings().first()
    if row is None:
        raise ValueError("User not found.")
    return _with_profile_completion(dict(row))


def get_profile_for_username(username: str) -> dict[str, Any]:
    """Return a user's profile plus pending profile update requests."""

    user = get_user_by_username(username)
    user["pending_profile_updates"] = [
        update for update in list_profile_update_requests(status="PENDING") if update["username"] == username
    ]
    return user


def submit_profile_update(username: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Submit a profile update request for admin approval."""

    user = get_user_by_username(username)
    changes = {
        field: _clean_optional(payload.get(field))
        for field in PROFILE_FIELDS
        if field in payload
    }
    changes = {
        field: value
        for field, value in changes.items()
        if str(user.get(field) or "") != value
    }
    if not changes:
        raise ValueError("No profile changes were submitted.")

    ensure_users_table()
    engine = create_monitor_engine()
    with engine.begin() as connection:
        row = connection.execute(
            text(
                """
                INSERT INTO data_quality_user_profile_updates (
                    user_id,
                    username,
                    requested_changes,
                    status
                )
                VALUES (
                    :user_id,
                    :username,
                    :requested_changes,
                    'PENDING'
                )
                RETURNING *
                """
            ),
            {
                "user_id": user["id"],
                "username": username,
                "requested_changes": json.dumps(changes, default=str),
            },
        ).mappings().one()
    return _decorate_profile_update(dict(row))


def list_profile_update_requests(status: str | None = None) -> list[dict[str, Any]]:
    """Return profile update requests for admin review."""

    ensure_users_table()
    conditions: list[str] = []
    params: dict[str, Any] = {}
    if status:
        conditions.append("p.status = :status")
        params["status"] = status.upper()
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    engine = create_monitor_engine()
    with engine.begin() as connection:
        rows = connection.execute(
            text(
                f"""
                SELECT
                    p.*,
                    u.full_name AS current_full_name,
                    u.email AS current_email,
                    u.job_title AS current_job_title,
                    u.department AS current_department,
                    u.phone_number AS current_phone_number,
                    u.role AS current_role
                FROM data_quality_user_profile_updates p
                LEFT JOIN data_quality_users u
                    ON u.id = p.user_id
                {where_clause}
                ORDER BY p.submitted_at DESC, p.id DESC
                """
            ),
            params,
        ).mappings().all()
    return [_decorate_profile_update(dict(row)) for row in rows]


def approve_profile_update_request(update_id: int, reviewed_by: str, notes: str | None = None) -> dict[str, Any]:
    """Approve a pending profile update and apply it to data_quality_users."""

    return _review_profile_update_request(update_id, reviewed_by, "APPROVED", notes)


def reject_profile_update_request(update_id: int, reviewed_by: str, notes: str | None = None) -> dict[str, Any]:
    """Reject a pending profile update without changing the user profile."""

    return _review_profile_update_request(update_id, reviewed_by, "REJECTED", notes)


def _review_profile_update_request(
    update_id: int,
    reviewed_by: str,
    status: str,
    notes: str | None = None,
) -> dict[str, Any]:
    ensure_users_table()
    engine = create_monitor_engine()
    with engine.begin() as connection:
        request_row = connection.execute(
            text("SELECT * FROM data_quality_user_profile_updates WHERE id = :update_id"),
            {"update_id": update_id},
        ).mappings().first()
        if request_row is None:
            raise ValueError("Profile update request not found.")
        if str(request_row.get("status") or "").upper() != "PENDING":
            raise ValueError("Profile update request has already been reviewed.")

        changes = _loads_json_dict(request_row.get("requested_changes"))
        if status == "APPROVED" and changes:
            assignments = [f"{field} = :{field}" for field in changes.keys() if field in PROFILE_FIELDS]
            if assignments:
                assignments.append("updated_at = CURRENT_TIMESTAMP")
                params = {**changes, "user_id": request_row["user_id"]}
                connection.execute(
                    text(
                        f"""
                        UPDATE data_quality_users
                        SET {", ".join(assignments)}
                        WHERE id = :user_id
                        """
                    ),
                    params,
                )

        reviewed = connection.execute(
            text(
                """
                UPDATE data_quality_user_profile_updates
                SET
                    status = :status,
                    reviewed_by = :reviewed_by,
                    reviewed_at = CURRENT_TIMESTAMP,
                    review_notes = :review_notes
                WHERE id = :update_id
                RETURNING *
                """
            ),
            {
                "update_id": update_id,
                "status": status,
                "reviewed_by": reviewed_by,
                "review_notes": _clean_optional(notes),
            },
        ).mappings().one()
    return _decorate_profile_update(dict(reviewed))


def _public_user(user: dict[str, Any]) -> dict[str, Any]:
    return _with_profile_completion({key: value for key, value in user.items() if key != "password_hash"})


def _with_profile_completion(user: dict[str, Any]) -> dict[str, Any]:
    required = ("full_name", "email", "job_title", "department", "phone_number")
    completed = sum(1 for field in required if str(user.get(field) or "").strip())
    user["profile_completion_percent"] = round((completed / len(required)) * 100)
    user["profile_completed"] = completed == len(required)
    return user


def _decorate_profile_update(row: dict[str, Any]) -> dict[str, Any]:
    row["requested_changes"] = _loads_json_dict(row.get("requested_changes"))
    return row


def _loads_json_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if not value:
        return {}
    try:
        loaded = json.loads(str(value))
        return loaded if isinstance(loaded, dict) else {}
    except json.JSONDecodeError:
        return {}


def _required_string(payload: dict[str, Any], field: str) -> str:
    value = str(payload.get(field) or "").strip()
    if not value:
        raise ValueError(f"{field} is required.")
    return value


def _clean_optional(value: Any) -> str:
    return str(value or "").strip()


def _normalize_role(role: Any) -> str:
    normalized = str(role or DEFAULT_ROLE).strip().lower()
    if normalized not in ALLOWED_ROLES:
        raise ValueError(f"Unsupported role '{role}'. Use one of: {', '.join(sorted(ALLOWED_ROLES))}.")
    return normalized
