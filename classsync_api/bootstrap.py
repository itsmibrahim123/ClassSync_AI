"""
Bootstrap utilities for initializing required database data.

This module ensures that core entities required for normal app operation
exist in the database. It reconciles the assumptions of local development
(which had seed data) with fresh production databases.

All functions are idempotent - safe to run on every startup.
"""

from sqlalchemy.orm import Session
from passlib.context import CryptContext
from classsync_core.models import Institution, User, UserRole


# Password hashing context (matches common FastAPI patterns)
# Using bcrypt with explicit configuration for compatibility
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Default values for bootstrap entities
DEFAULT_INSTITUTION_NAME = "Default Institution"
DEFAULT_INSTITUTION_CODE = "DEFAULT"

DEFAULT_USER_EMAIL = "admin@classsync.local"
DEFAULT_USER_NAME = "Demo Admin"
DEFAULT_USER_PASSWORD = "changeme123"  # Short, stable password for bootstrap

# bcrypt has a 72-byte limit on passwords
BCRYPT_MAX_BYTES = 72


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt with safety checks.

    Handles:
    - bcrypt 72-byte password limit (truncates if needed)
    - passlib/bcrypt version compatibility issues

    Args:
        password: The password to hash

    Returns:
        The hashed password string

    Raises:
        RuntimeError: If hashing fails for any reason
    """
    try:
        # Ensure password is a string and strip whitespace
        pwd = str(password).strip()

        # Enforce bcrypt's 72-byte limit to avoid passlib errors
        pwd_bytes = pwd.encode("utf-8")
        if len(pwd_bytes) > BCRYPT_MAX_BYTES:
            # Truncate to 72 bytes, safely decoding back to string
            pwd = pwd_bytes[:BCRYPT_MAX_BYTES].decode("utf-8", errors="ignore")

        return pwd_context.hash(pwd)

    except Exception as e:
        # hashed_password is NOT nullable in User model, so we cannot use placeholder
        raise RuntimeError(
            f"Bootstrap failed to hash password; check bcrypt/passlib versions. "
            f"Error: {type(e).__name__}: {e}"
        )


def ensure_default_institution(db: Session) -> Institution:
    """
    Ensure at least one institution exists in the database.

    This function is idempotent - it only creates a default institution
    if no institutions exist. Safe to call multiple times.

    Args:
        db: SQLAlchemy database session

    Returns:
        The first/default institution (existing or newly created)
    """
    # Check if any institution exists
    existing = db.query(Institution).first()

    if existing is not None:
        return existing

    # No institutions exist - create a default one
    default_institution = Institution(
        name=DEFAULT_INSTITUTION_NAME,
        code=DEFAULT_INSTITUTION_CODE,
        is_active=True
    )

    db.add(default_institution)
    db.flush()  # Flush to get the ID without committing

    return default_institution


def ensure_default_user(db: Session, institution: Institution) -> User:
    """
    Ensure at least one user exists in the database.

    This function is idempotent - it only creates a default user
    if no users exist. Safe to call multiple times.

    Args:
        db: SQLAlchemy database session
        institution: The institution to link the user to

    Returns:
        The first/default user (existing or newly created)
    """
    # Check if any user exists
    existing = db.query(User).first()

    if existing is not None:
        return existing

    # No users exist - create a default admin user
    default_user = User(
        institution_id=institution.id,
        email=DEFAULT_USER_EMAIL,
        hashed_password=get_password_hash(DEFAULT_USER_PASSWORD),
        full_name=DEFAULT_USER_NAME,
        role=UserRole.ADMIN,
        is_active=True
    )

    db.add(default_user)
    db.flush()  # Flush to get the ID without committing

    return default_user


def bootstrap_database(db: Session) -> None:
    """
    Bootstrap all required database entities for app operation.

    This is the main entry point for database bootstrapping.
    It ensures all core entities exist in the correct order
    (respecting foreign key constraints).

    Order of operations:
    1. Institution (no FK dependencies)
    2. User (depends on Institution)

    This function is idempotent and safe to call on every startup.

    Args:
        db: SQLAlchemy database session
    """
    # Step 1: Ensure institution exists (no FK dependencies)
    institution = ensure_default_institution(db)

    # Step 2: Ensure user exists (depends on institution)
    ensure_default_user(db, institution)

    # Commit all changes in a single transaction
    db.commit()


def get_default_institution(db: Session) -> Institution:
    """
    Get the default/first institution from the database.

    Use this instead of hardcoding institution_id=1.

    Args:
        db: SQLAlchemy database session

    Returns:
        The first institution in the database

    Raises:
        ValueError: If no institutions exist (bootstrap not run)
    """
    institution = db.query(Institution).first()
    if institution is None:
        raise ValueError("No institution exists. Ensure bootstrap_database() was called.")
    return institution


def get_default_user(db: Session) -> User:
    """
    Get the default/first user from the database.

    Use this instead of hardcoding user_id=1.

    Args:
        db: SQLAlchemy database session

    Returns:
        The first user in the database

    Raises:
        ValueError: If no users exist (bootstrap not run)
    """
    user = db.query(User).first()
    if user is None:
        raise ValueError("No user exists. Ensure bootstrap_database() was called.")
    return user
