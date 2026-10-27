import json
import tempfile
import unittest
from pathlib import Path
from urllib.parse import unquote, urlsplit
from unittest.mock import patch

import auth
from app import activities, app


async def asgi_request(method, url, body=b"", cookie=None):
    parsed_url = urlsplit(url)
    headers = [(b"host", b"testserver")]
    if body:
        headers.extend(
            [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode("ascii")),
            ]
        )
    if cookie:
        headers.append((b"cookie", cookie.encode("ascii")))

    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": unquote(parsed_url.path),
        "raw_path": parsed_url.path.encode("ascii"),
        "query_string": parsed_url.query.encode("ascii"),
        "root_path": "",
        "headers": headers,
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
    }
    messages = []
    request_sent = False

    async def receive():
        nonlocal request_sent
        if request_sent:
            return {"type": "http.disconnect"}
        request_sent = True
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message):
        messages.append(message)

    await app(scope, receive, send)
    response_start = next(message for message in messages if message["type"] == "http.response.start")
    response_body = b"".join(
        message.get("body", b"")
        for message in messages
        if message["type"] == "http.response.body"
    )
    return response_start["status"], response_start["headers"], response_body


class TeacherAuthApiTests(unittest.IsolatedAsyncioTestCase):
    async def test_login_gates_registration_changes_and_logout_revokes_session(self):
        email = "admin-mode-test@mergington.edu"
        self.addCleanup(
            lambda: activities["Chess Club"]["participants"].remove(email)
            if email in activities["Chess Club"]["participants"]
            else None
        )
        credentials = [auth.make_password_record("teacher", "test-password")]

        with tempfile.TemporaryDirectory() as directory:
            credentials_path = Path(directory) / "teachers.json"
            credentials_path.write_text(json.dumps(credentials), encoding="utf-8")
            with patch.object(auth, "TEACHERS_FILE", credentials_path):
                auth.sessions.clear()

                anonymous_signup = await asgi_request(
                    "POST", f"/activities/Chess%20Club/signup?email={email}"
                )
                anonymous_unregister = await asgi_request(
                    "DELETE",
                    "/activities/Chess%20Club/unregister?email=michael%40mergington.edu",
                )
                self.assertEqual(anonymous_signup[0], 401)
                self.assertEqual(anonymous_unregister[0], 401)

                login_status, login_headers, _ = await asgi_request(
                    "POST",
                    "/auth/login",
                    json.dumps(
                        {"username": "teacher", "password": "test-password"}
                    ).encode("utf-8"),
                )
                self.assertEqual(login_status, 200)
                set_cookie = next(
                    value.decode("latin-1")
                    for name, value in login_headers
                    if name.lower() == b"set-cookie"
                )
                cookie = set_cookie.split(";", maxsplit=1)[0]

                authenticated_status = await asgi_request(
                    "GET", "/auth/me", cookie=cookie
                )
                self.assertEqual(authenticated_status[0], 200)
                self.assertTrue(json.loads(authenticated_status[2])["authenticated"])

                signup = await asgi_request(
                    "POST", f"/activities/Chess%20Club/signup?email={email}", cookie=cookie
                )
                self.assertEqual(signup[0], 200)
                self.assertIn(email, activities["Chess Club"]["participants"])

                unregister = await asgi_request(
                    "DELETE",
                    f"/activities/Chess%20Club/unregister?email={email}",
                    cookie=cookie,
                )
                self.assertEqual(unregister[0], 200)

                logout = await asgi_request("POST", "/auth/logout", cookie=cookie)
                self.assertEqual(logout[0], 200)
                revoked_status = await asgi_request("GET", "/auth/me", cookie=cookie)
                self.assertFalse(json.loads(revoked_status[2])["authenticated"])


if __name__ == "__main__":
    unittest.main()