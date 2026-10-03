"""パスワード変更・再設定の公開API契約。"""

import time

import caliboo_api.db as db
from caliboo_api.extension_models import PasswordReset
from caliboo_api.models import User


NEW_PASSWORD = "new-secret-12345"


def test_change_password_requires_current_password_and_revokes_sessions(client, login_as):
    other_session = login_as("yuki")
    bad = client.post("/api/auth/change-password", json={
        "currentPassword": "wrong", "newPassword": NEW_PASSWORD,
    })
    assert bad.status_code == 401
    assert client.get("/api/auth/me").status_code == 200

    changed = client.post("/api/auth/change-password", json={
        "currentPassword": "caliboo-yuki", "newPassword": NEW_PASSWORD,
    })
    assert changed.status_code == 204
    assert client.get("/api/auth/me").status_code == 401
    assert other_session.get("/api/auth/me").status_code == 401
    assert client.post("/api/auth/login", json={
        "loginId": "yuki", "password": "caliboo-yuki",
    }).status_code == 401
    assert client.post("/api/auth/login", json={
        "loginId": "yuki", "password": NEW_PASSWORD,
    }).status_code == 200


def test_reset_code_is_admin_only_one_time_and_replaces_old_code(
    admin_client, client, anonymous_client,
):
    user_id = client.get("/api/auth/me").json()["id"]
    path = f"/api/users/{user_id}/password-reset-code"
    assert anonymous_client.post(path).status_code == 401
    assert client.post(path).status_code == 403
    first = admin_client.post(path)
    assert first.status_code == 200
    assert first.headers["cache-control"] == "no-store"
    old_code = first.json()["resetCode"]
    with db.session_scope() as session:
        reset = session.get(PasswordReset, user_id)
        assert reset.token_hash != old_code
    new_code = admin_client.post(path).json()["resetCode"]
    assert new_code != old_code
    body = {"loginId": "yuki", "resetCode": old_code, "newPassword": NEW_PASSWORD}
    assert anonymous_client.post("/api/auth/reset-password", json=body).status_code == 401
    body["resetCode"] = new_code
    assert anonymous_client.post("/api/auth/reset-password", json=body).status_code == 204
    assert client.get("/api/auth/me").status_code == 401
    assert anonymous_client.post("/api/auth/reset-password", json=body).status_code == 401
    assert anonymous_client.post("/api/auth/login", json={
        "loginId": "yuki", "password": NEW_PASSWORD,
    }).status_code == 200


def test_reset_unknown_expired_and_inactive_have_same_error(
    admin_client, client, anonymous_client,
):
    user_id = client.get("/api/auth/me").json()["id"]
    code = admin_client.post(f"/api/users/{user_id}/password-reset-code").json()["resetCode"]
    path = "/api/auth/reset-password"
    body = {"loginId": "yuki", "resetCode": code, "newPassword": NEW_PASSWORD}
    unknown = anonymous_client.post(path, json={**body, "loginId": "unknown"})
    with db.session_scope() as session:
        session.get(PasswordReset, user_id).expires_at = int(time.time()) - 1
        session.commit()
    expired = anonymous_client.post(path, json=body)
    assert unknown.status_code == expired.status_code == 401
    assert unknown.json() == expired.json()


def test_reset_attempts_are_limited_by_source(admin_client, client, anonymous_client):
    user_id = client.get("/api/auth/me").json()["id"]
    admin_client.post(f"/api/users/{user_id}/password-reset-code")
    body = {"loginId": "yuki", "resetCode": "incorrect", "newPassword": NEW_PASSWORD}
    for _ in range(20):
        assert anonymous_client.post("/api/auth/reset-password", json=body).status_code == 401
    limited = anonymous_client.post("/api/auth/reset-password", json=body)
    assert limited.status_code == 429
    assert int(limited.headers["retry-after"]) > 0


def test_role_change_invalidates_previously_issued_reset_code(
    admin_client, client, anonymous_client,
):
    user_id = client.get("/api/auth/me").json()["id"]
    code = admin_client.post(f"/api/users/{user_id}/password-reset-code").json()["resetCode"]
    account = next(row for row in admin_client.get("/api/users").json()["users"]
                   if row["id"] == user_id)
    changed = admin_client.post(f"/api/users/{user_id}", json={
        "displayName": account["displayName"], "role": "admin", "active": True,
        "departmentId": account["departmentId"],
    })
    assert changed.status_code == 200
    assert anonymous_client.post("/api/auth/reset-password", json={
        "loginId": "yuki", "resetCode": code, "newPassword": NEW_PASSWORD,
    }).status_code == 401


def test_password_validation_and_no_password_user(client, anonymous_client):
    assert client.post("/api/auth/change-password", json={
        "currentPassword": "caliboo-yuki", "newPassword": "short",
    }).status_code == 422
    assert client.post("/api/auth/change-password", json={
        "currentPassword": "caliboo-yuki", "newPassword": "caliboo-yuki",
    }).status_code == 422
    with db.session_scope() as session:
        session.query(User).filter_by(login_id="yuki").first().password_hash = None
        session.commit()
    assert client.post("/api/auth/change-password", json={
        "currentPassword": "caliboo-yuki", "newPassword": NEW_PASSWORD,
    }).status_code == 401
    assert anonymous_client.post("/api/auth/reset-password", json={
        "loginId": "yuki", "resetCode": "missing", "newPassword": "short",
    }).status_code == 422
