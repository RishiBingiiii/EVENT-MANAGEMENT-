"""
Password hashing helpers.

Uses salted SHA-256. This is fine for a learning project, but if you ever
deploy this for real users, switch to a dedicated library like bcrypt or
passlib instead.
"""

import hashlib
import secrets


def hash_password(password: str) -> str:
    """Return a 'salt$hash' string for safe storage in the database."""
    salt = secrets.token_hex(16)
    digest = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return f"{salt}${digest}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Check a plaintext password against a stored 'salt$hash' string."""
    try:
        salt, digest = stored_hash.split("$")
    except ValueError:
        return False
    candidate = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return secrets.compare_digest(candidate, digest)
