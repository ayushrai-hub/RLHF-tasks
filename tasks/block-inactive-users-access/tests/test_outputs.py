"""
Verifier tests for the block-inactive-users-access task.

The running Node.js API is expected at http://localhost:3000.
The PostgreSQL database is accessible via the DATABASE_URL environment variable.

Tests validate that:
- Inactive users cannot log in.
- Inactive users cannot refresh tokens even with a valid refresh cookie.
- Inactive users cannot use an existing access token on protected routes.
- Active users retain full access (login, token use, admin routes).
- User listings exclude inactive accounts.
- Inactive admin users are blocked from admin routes.
- Deactivated accounts cannot re-register with the same email.
"""

import os

import psycopg2
import pytest
import requests

BASE_URL = "http://localhost:3000"
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:terminus_pg_pass@localhost:5432/appdb",
)


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def _get_conn():
    return psycopg2.connect(DATABASE_URL)


def _set_user_active(email: str, active: bool) -> None:
    """Directly flip the active flag for a user in the database."""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute('UPDATE "User" SET active = %s WHERE email = %s', (active, email))
        conn.commit()
    finally:
        conn.close()


def _set_user_role(email: str, role_name: str) -> None:
    """Promote a user to the given role name (e.g. 'ADMIN') by updating roleId."""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT id FROM "Role" WHERE name = %s', (role_name,))
            row = cur.fetchone()
            assert row is not None, f"Role '{role_name}' not found in database"
            cur.execute('UPDATE "User" SET "roleId" = %s WHERE email = %s', (row[0], email))
        conn.commit()
    finally:
        conn.close()


def _register(email: str, password: str = "TestPass123!") -> requests.Response:
    return requests.post(
        f"{BASE_URL}/auth/register",
        json={"email": email, "password": password},
        timeout=10,
    )


def _login(email: str, password: str = "TestPass123!") -> requests.Response:
    return requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": email, "password": password},
        timeout=10,
    )


def _extract_access_token(res: requests.Response) -> str:
    return res.json()["data"]["accessToken"]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clean_test_users():
    """
    Remove any test users created during this test from the database before
    each test so tests are fully independent.
    """
    test_emails = [
        "inactive_login@test.com",
        "inactive_token@test.com",
        "inactive_refresh@test.com",
        "active_user@test.com",
        "admin_user@test.com",
        "inactive_admin@test.com",
        "reregister_user@test.com",
        "list_user_a@test.com",
        "list_user_b@test.com",
    ]
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            for email in test_emails:
                cur.execute('DELETE FROM "RefreshToken" USING "User" '
                            'WHERE "RefreshToken"."userId" = "User"."id" AND "User"."email" = %s',
                            (email,))
                cur.execute('DELETE FROM "User" WHERE email = %s', (email,))
        conn.commit()
    finally:
        conn.close()
    yield
    # Teardown: same cleanup after test
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            for email in test_emails:
                cur.execute('DELETE FROM "RefreshToken" USING "User" '
                            'WHERE "RefreshToken"."userId" = "User"."id" AND "User"."email" = %s',
                            (email,))
                cur.execute('DELETE FROM "User" WHERE email = %s', (email,))
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Tests: inactive user cannot log in
# ---------------------------------------------------------------------------

class TestInactiveUserLogin:
    def test_inactive_user_login_is_rejected(self):
        """An inactive user must not receive a successful login response (HTTP 200)."""
        email = "inactive_login@test.com"
        # Register to create the account
        reg_res = _register(email)
        assert reg_res.status_code == 201, f"Registration failed: {reg_res.text}"

        # Deactivate the user directly in the database
        _set_user_active(email, False)

        # Attempt login — must not succeed
        res = _login(email)
        assert res.status_code == 401, (
            f"Inactive user login returned HTTP {res.status_code}. "
            "Expected 401 — inactive accounts must be rejected at login."
        )
        body = res.json()
        assert body.get("success") is False, (
            "Response body must have success=false for inactive user login."
        )

    def test_active_user_login_succeeds(self):
        """An active user must still be able to log in after the fix is applied."""
        email = "active_user@test.com"
        reg_res = _register(email)
        assert reg_res.status_code == 201

        # Account is active by default — login should work
        res = _login(email)
        assert res.status_code == 200, (
            f"Active user login failed with HTTP {res.status_code}: {res.text}"
        )
        assert res.json().get("success") is True
        assert res.json().get("data", {}).get("accessToken"), "No access token returned for active user."


# ---------------------------------------------------------------------------
# Tests: inactive user cannot use an existing access token
# ---------------------------------------------------------------------------

class TestInactiveUserAccessToken:
    def test_existing_access_token_rejected_after_deactivation(self):
        """
        A token issued before deactivation must be rejected on protected routes
        once the account is set to inactive.
        """
        email = "inactive_token@test.com"
        reg_res = _register(email)
        assert reg_res.status_code == 201

        access_token = _extract_access_token(reg_res)

        # Deactivate the user AFTER obtaining a valid token
        _set_user_active(email, False)

        # Try to hit a protected route with the now-stale token
        res = requests.get(
            f"{BASE_URL}/users/all",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        assert res.status_code == 401, (
            f"Protected route returned HTTP {res.status_code} for an inactive user's token. "
            "Expected 401 — inactive accounts must be blocked even with a valid JWT."
        )
        assert res.json().get("success") is False

    def test_active_user_access_token_accepted(self):
        """Active user's access token must still work on authenticated routes."""
        email = "active_user@test.com"
        reg_res = _register(email)
        assert reg_res.status_code == 201

        access_token = _extract_access_token(reg_res)

        # A freshly registered user has the USER role, so /users/all returns 403 (not 401)
        res = requests.get(
            f"{BASE_URL}/users/all",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        # 403 means the token was accepted (authenticated) but the role check failed —
        # this is the expected behaviour for an active USER-role account.
        assert res.status_code in (200, 403), (
            f"Active user's token was unexpectedly rejected with HTTP {res.status_code}. "
            "An active account must pass authentication (401 is not acceptable)."
        )


# ---------------------------------------------------------------------------
# Tests: inactive user cannot refresh tokens
# ---------------------------------------------------------------------------

class TestInactiveUserRefreshToken:
    def test_refresh_rejected_after_deactivation(self):
        """
        A refresh token obtained before deactivation must not produce a new
        access token once the account is set inactive.
        """
        email = "inactive_refresh@test.com"

        # Register and capture the refresh-token cookie
        reg_res = _register(email)
        assert reg_res.status_code == 201

        # Build a session that carries the cookie
        session = requests.Session()
        for cookie in reg_res.cookies:
            session.cookies.set(cookie.name, cookie.value)

        # Deactivate the user AFTER obtaining a valid refresh token
        _set_user_active(email, False)

        # Attempt to refresh — must be rejected
        res = session.post(f"{BASE_URL}/auth/refresh", json={}, timeout=10)
        assert res.status_code == 401, (
            f"Inactive user refresh returned HTTP {res.status_code}. "
            "Expected 401 — token refresh must be rejected for inactive accounts."
        )
        body = res.json()
        assert body.get("success") is False, (
            "Response body must have success=false when refresh is denied for inactive user."
        )

    def test_active_user_refresh_succeeds(self):
        """An active user must still be able to refresh tokens after the fix."""
        email = "active_user@test.com"

        session = requests.Session()
        reg_res = session.post(
            f"{BASE_URL}/auth/register",
            json={"email": email, "password": "TestPass123!"},
            timeout=10,
        )
        assert reg_res.status_code == 201

        res = session.post(f"{BASE_URL}/auth/refresh", json={}, timeout=10)
        assert res.status_code == 200, (
            f"Active user refresh failed with HTTP {res.status_code}: {res.text}"
        )
        assert res.json().get("success") is True
        assert res.json().get("data", {}).get("accessToken"), "No new access token returned."


# ---------------------------------------------------------------------------
# Tests: active admin user can still access admin routes
# ---------------------------------------------------------------------------

class TestActiveAdminAccess:
    def test_active_admin_can_access_admin_route(self):
        """
        An active ADMIN-role user must be able to reach /users/all (HTTP 200)
        after the inactive-user fix is applied.

        This guards against implementations that short-circuit the middleware
        chain incorrectly and accidentally block role-based authorization.
        """
        email = "admin_user@test.com"
        reg_res = _register(email)
        assert reg_res.status_code == 201, f"Registration failed: {reg_res.text}"

        # Promote to ADMIN directly in the database
        _set_user_role(email, "ADMIN")

        # Log in to obtain a fresh access token carrying the ADMIN role
        login_res = _login(email)
        assert login_res.status_code == 200, (
            f"Active admin login failed with HTTP {login_res.status_code}: {login_res.text}"
        )
        token = _extract_access_token(login_res)

        # Admin-only route must return 200 for an active ADMIN user
        res = requests.get(
            f"{BASE_URL}/users/all",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        assert res.status_code == 200, (
            f"Active admin received HTTP {res.status_code} on /users/all. "
            "An active ADMIN account must be able to access admin-only routes."
        )
        assert isinstance(res.json(), list), (
            "/users/all must return a list of users for an active ADMIN account."
        )


# ---------------------------------------------------------------------------
# Tests: user listing excludes inactive accounts
# ---------------------------------------------------------------------------

class TestUserListExcludesInactive:
    def test_user_list_excludes_inactive_accounts(self):
        """The /users/all endpoint must not return users whose active flag is false."""
        email_a = "list_user_a@test.com"
        email_b = "list_user_b@test.com"

        # Create two users
        assert _register(email_a).status_code == 201
        assert _register(email_b).status_code == 201

        # Deactivate user B
        _set_user_active(email_b, False)

        # Promote user A to ADMIN so they can call /users/all
        _set_user_role(email_a, "ADMIN")
        login_res = _login(email_a)
        assert login_res.status_code == 200
        token = _extract_access_token(login_res)

        res = requests.get(
            f"{BASE_URL}/users/all",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        assert res.status_code == 200
        users = res.json()
        assert isinstance(users, list)

        returned_emails = {u.get("email") for u in users if isinstance(u, dict)}
        assert email_a in returned_emails, (
            "Active user must appear in /users/all listing."
        )
        assert email_b not in returned_emails, (
            "Inactive user must NOT appear in /users/all listing."
        )


# ---------------------------------------------------------------------------
# Tests: inactive admin blocked from admin routes
# ---------------------------------------------------------------------------

class TestInactiveAdminBlocked:
    def test_inactive_admin_cannot_access_admin_route(self):
        """An admin whose account is deactivated must receive HTTP 401 on /users/all."""
        email = "inactive_admin@test.com"
        assert _register(email).status_code == 201

        _set_user_role(email, "ADMIN")

        # Log in to get a token while active
        login_res = _login(email)
        assert login_res.status_code == 200
        token = _extract_access_token(login_res)

        # Now deactivate
        _set_user_active(email, False)

        res = requests.get(
            f"{BASE_URL}/users/all",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        assert res.status_code == 401, (
            f"Inactive admin received HTTP {res.status_code} on /users/all. "
            "Expected 401 — deactivated admin accounts must be blocked from admin routes."
        )
        assert res.json().get("success") is False


# ---------------------------------------------------------------------------
# Tests: deactivated account cannot re-register
# ---------------------------------------------------------------------------

class TestDeactivatedUserRegistration:
    def test_deactivated_user_cannot_reregister(self):
        """Registering with an email that belongs to a deactivated account must be rejected."""
        email = "reregister_user@test.com"

        # Register once
        reg1 = _register(email)
        assert reg1.status_code == 201

        # Deactivate the account
        _set_user_active(email, False)

        # Attempt to register again with the same email — must fail
        reg2 = _register(email)
        assert reg2.status_code in (409, 400), (
            f"Re-registration with deactivated email returned HTTP {reg2.status_code}. "
            "Expected 409 or 400 — deactivated accounts must not be re-registerable."
        )
        body = reg2.json()
        assert body.get("success") is False, (
            "Re-registration of deactivated account must return success=false."
        )
        assert "user already exists" in body.get("message", "").lower(), (
            "Re-registration must be rejected by application logic with a 'user already exists' "
            "message, not by a generic database constraint error."
        )

