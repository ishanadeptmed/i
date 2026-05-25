"""Local JSON auth for store owners and managers."""

from __future__ import annotations

import hashlib
import json
import os
import secrets
from typing import Any

from config import DATA_DIR, USERS_FILE
from services.bootstrap import get_logger
from Drug_EDA.exception import format_error, raise_custom

logger = get_logger("services.auth")

PBKDF2_ITERATIONS = 260_000
SALT_BYTES = 16


def _ensure_data_dir() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)


def _empty_store() -> dict[str, list]:
    return {"owners": [], "managers": []}


def load_users() -> dict[str, list]:
    _ensure_data_dir()
    if not os.path.exists(USERS_FILE):
        logger.debug("No users file at %s; returning empty store", USERS_FILE)
        return _empty_store()
    try:
        with open(USERS_FILE, encoding="utf-8") as f:
            data = json.load(f)
        data.setdefault("owners", [])
        data.setdefault("managers", [])
        logger.debug(
            "Loaded users: %d owners, %d managers",
            len(data["owners"]),
            len(data["managers"]),
        )
        return data
    except Exception as exc:
        logger.exception("Failed to load users from %s", USERS_FILE)
        raise_custom(exc)


def save_users(data: dict[str, list]) -> None:
    _ensure_data_dir()
    try:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        logger.info(
            "Saved users: %d owners, %d managers",
            len(data.get("owners", [])),
            len(data.get("managers", [])),
        )
    except Exception as exc:
        logger.exception("Failed to save users to %s", USERS_FILE)
        raise_custom(exc)


def _hash_password(password: str) -> str:
    salt = secrets.token_bytes(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )
    return f"{salt.hex()}:{digest.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, digest_hex = stored.split(":", 1)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
    except ValueError:
        logger.warning("Invalid password hash format")
        return False
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )
    return secrets.compare_digest(digest, expected)


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _parse_list_field(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def signup_owner(
    email: str,
    password: str,
    store_ids: str,
    manager_emails: str,
) -> tuple[bool, str]:
    email = _normalize_email(email)
    logger.info("Owner signup attempt: %s", email)
    try:
        if not email or not password:
            logger.warning("Owner signup rejected: missing email or password")
            return False, "Email and password are required."

        stores = _parse_list_field(store_ids)
        managers = [_normalize_email(m) for m in _parse_list_field(manager_emails)]
        if not stores:
            logger.warning("Owner signup rejected for %s: no store IDs", email)
            return False, "At least one store ID is required."

        data = load_users()
        if any(o["email"] == email for o in data["owners"]):
            logger.warning("Owner signup rejected: %s already exists", email)
            return False, "Owner email already registered."
        if any(m["email"] == email for m in data["managers"]):
            logger.warning("Owner signup rejected: %s already a manager", email)
            return False, "Email already registered as a manager."

        data["owners"].append(
            {
                "email": email,
                "password_hash": _hash_password(password),
                "store_ids": stores,
                "manager_emails": managers,
            }
        )
        save_users(data)
        logger.info("Owner signup success: %s stores=%s managers=%s", email, stores, managers)
        return True, "Owner account created."
    except Exception as exc:
        logger.exception("Owner signup failed for %s", email)
        return False, format_error(exc)


def is_manager_whitelisted(email: str) -> tuple[bool, str | None]:
    email = _normalize_email(email)
    data = load_users()
    for owner in data["owners"]:
        if email in owner.get("manager_emails", []):
            logger.debug("Manager %s whitelisted by owner %s", email, owner["email"])
            return True, owner["email"]
    logger.debug("Manager %s not whitelisted", email)
    return False, None


def signup_manager(email: str, password: str) -> tuple[bool, str]:
    email = _normalize_email(email)
    logger.info("Manager signup attempt: %s", email)
    try:
        if not email or not password:
            logger.warning("Manager signup rejected: missing email or password")
            return False, "Email and password are required."

        allowed, owner_email = is_manager_whitelisted(email)
        if not allowed or not owner_email:
            logger.warning("Manager signup rejected: %s not whitelisted", email)
            return False, "Email is not whitelisted by any store owner."

        data = load_users()
        if any(m["email"] == email for m in data["managers"]):
            logger.warning("Manager signup rejected: %s already registered", email)
            return False, "Manager already registered. Please log in."

        data["managers"].append(
            {
                "email": email,
                "password_hash": _hash_password(password),
                "owner_email": owner_email,
            }
        )
        save_users(data)
        logger.info("Manager signup success: %s owner=%s", email, owner_email)
        return True, "Manager account created."
    except Exception as exc:
        logger.exception("Manager signup failed for %s", email)
        return False, format_error(exc)


def login_manager(email: str, password: str) -> tuple[bool, str, dict[str, Any] | None]:
    email = _normalize_email(email)
    logger.info("Manager login attempt: %s", email)
    try:
        data = load_users()
        manager = next((m for m in data["managers"] if m["email"] == email), None)
        if not manager:
            logger.warning("Manager login failed: %s not found", email)
            return False, "Manager not found. Sign up first.", None
        if not _verify_password(password, manager["password_hash"]):
            logger.warning("Manager login failed: invalid password for %s", email)
            return False, "Invalid password.", None

        owner = next((o for o in data["owners"] if o["email"] == manager["owner_email"]), None)
        if not owner:
            logger.error("Manager %s linked owner %s missing", email, manager["owner_email"])
            return False, "Linked owner account not found.", None

        session = {
            "role": "manager",
            "email": email,
            "owner_email": owner["email"],
            "store_ids": owner.get("store_ids", []),
        }
        logger.info("Manager login success: %s stores=%s", email, session["store_ids"])
        return True, "Logged in successfully.", session
    except Exception as exc:
        logger.exception("Manager login failed for %s", email)
        return False, format_error(exc), None


def get_owner_by_email(email: str) -> dict[str, Any] | None:
    email = _normalize_email(email)
    data = load_users()
    return next((o for o in data["owners"] if o["email"] == email), None)
