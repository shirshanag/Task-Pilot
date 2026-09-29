import hashlib
import hmac
import os
import sqlite3

from .database import db_run


def hash_password(
    password: str,
    salt: bytes | None = None
) -> str:

    salt = salt or os.urandom(16)

    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        salt,
        200_000
    )

    return f"{salt.hex()}${digest.hex()}"


def check_password(
    password: str,
    stored: str
) -> bool:

    salt_hex, digest_hex = stored.split("$")

    new = hash_password(
        password,
        bytes.fromhex(salt_hex)
    ).split("$")[1]

    return hmac.compare_digest(
        new,
        digest_hex
    )


def signup_user(
    username: str,
    password: str
):

    username = username.strip().lower()

    if len(username) < 3:
        return (
            False,
            "Username must be at least 3 characters."
        )

    if len(password) < 6:
        return (
            False,
            "Password must be at least 6 characters."
        )

    try:

        db_run(
            """
            INSERT INTO users
            (username, password_hash)
            VALUES (?, ?)
            """,
            (
                username,
                hash_password(password)
            )
        )

        return (
            True,
            "Account created! You can log in now."
        )

    except sqlite3.IntegrityError:

        return (
            False,
            "That username is already taken."
        )


def login_user(
    username: str,
    password: str
):

    rows = db_run(
        """
        SELECT
            id,
            username,
            password_hash

        FROM users

        WHERE username = ?
        """,
        (
            username.strip().lower(),
        ),
        fetch=True
    )

    if rows and check_password(
        password,
        rows[0]["password_hash"]
    ):

        return {
            "id": rows[0]["id"],
            "username": rows[0]["username"]
        }

    return None