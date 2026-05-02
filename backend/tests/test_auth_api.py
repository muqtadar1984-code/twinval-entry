"""Auth router integration tests."""


def test_health_is_open(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_me_requires_authentication(client):
    r = client.get("/auth/me")
    assert r.status_code == 401


def test_me_returns_current_user(intern_client, intern_user):
    r = intern_client.get("/auth/me")
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == intern_user.email
    assert body["role"] == "intern"
    assert body["name"] == intern_user.name


def test_login_success_sets_cookies(client, intern_user):
    r = client.post(
        "/auth/login",
        json={"email": intern_user.email, "password": "intern-password-123"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["role"] == "intern"
    assert body["email"] == intern_user.email
    # The TestClient should have access_token set on its cookie jar
    cookies = {c.name: c.value for c in client.cookies.jar}
    assert "access_token" in cookies
    assert "refresh_token" in cookies


def test_login_with_wrong_password_rejected(client, intern_user):
    r = client.post(
        "/auth/login",
        json={"email": intern_user.email, "password": "WRONG"},
    )
    assert r.status_code == 401


def test_login_with_unknown_email_rejected(client):
    r = client.post(
        "/auth/login",
        json={"email": "ghost@nowhere.com", "password": "x"},
    )
    assert r.status_code == 401


def test_invalid_token_returns_401(client):
    client.headers.update({"Authorization": "Bearer not-a-real-token"})
    r = client.get("/auth/me")
    assert r.status_code == 401


def test_admin_role_blocked_for_intern_endpoints(intern_client):
    # Intern cannot access admin routes
    r = intern_client.get("/admin/observations")
    assert r.status_code == 403
