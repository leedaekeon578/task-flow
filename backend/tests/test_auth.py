from datetime import datetime

from support import ApiTestCase

PW = "correct-horse"


def creds(email="a@example.com", password=PW):
    return {"email": email, "password": password}


class SignupTest(ApiTestCase):
    def test_signup_logs_in_and_hides_secrets(self):
        c = self.new_client()
        r = c.post("/api/auth/signup", json=creds())
        self.assertEqual(r.status_code, 201)
        self.assertEqual(set(r.json()), {"id", "email"})
        cookie = r.headers["set-cookie"].lower()
        self.assertIn("httponly", cookie)
        self.assertIn("samesite=lax", cookie)
        self.assertIn("max-age=1800", cookie)
        me = c.get("/api/auth/me")
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()["email"], "a@example.com")
        self.assertEqual(set(me.json()), {"id", "email"})

    def test_password_stored_only_as_argon2_hash(self):
        self.new_client().post("/api/auth/signup", json=creds())
        (h,) = self.sql("SELECT password_hash FROM users WHERE email='a@example.com'")[0]
        self.assertTrue(h.startswith("$argon2"))
        self.assertNotIn(PW.encode(), self.db_path.read_bytes())

    def test_cookie_value_is_not_stored(self):
        c = self.new_client()
        c.post("/api/auth/signup", json=creds())
        token = c.cookies.get("session")
        (stored,) = self.sql("SELECT token_hash FROM sessions")[0]
        self.assertNotEqual(stored, token)
        self.assertNotIn(token.encode(), self.db_path.read_bytes())

    def test_session_expires_in_30_minutes(self):
        self.new_client().post("/api/auth/signup", json=creds())
        created, expires = self.sql("SELECT created_at, expires_at FROM sessions")[0]
        delta = datetime.fromisoformat(expires) - datetime.fromisoformat(created)
        self.assertEqual(delta.total_seconds(), 1800)

    def test_duplicate_email_is_409_case_insensitive(self):
        self.new_client().post("/api/auth/signup", json=creds())
        for email in ("a@example.com", "A@Example.COM"):
            r = self.new_client().post("/api/auth/signup", json=creds(email, "another-pass"))
            self.assertEqual(r.status_code, 409)
        self.assertEqual(self.sql("SELECT count(*) FROM users WHERE email LIKE 'a@%'"), [(1,)])

    def test_invalid_input_is_422_and_creates_nothing(self):
        before = self.sql("SELECT count(*) FROM users")
        for body in (
            creds(password="short"),
            creds(password=""),
            creds(email="not-an-email"),
            creds(email=""),
            {"email": "a@example.com"},
            {},
            creds(password="x" * 129),
        ):
            with self.subTest(body=body):
                r = self.new_client().post("/api/auth/signup", json=body)
                self.assertEqual(r.status_code, 422)
        self.assertEqual(self.sql("SELECT count(*) FROM users"), before)
        self.assertEqual(self.sql("SELECT count(*) FROM sessions"), [(0,)])


class MigratedAccountTest(ApiTestCase):
    def test_migrated_account_cannot_login_until_first_signup(self):
        r = self.new_client().post("/api/auth/login", json=creds("migrated@test.com", "anything1"))
        self.assertEqual(r.status_code, 401)
        self.assertEqual(self.sql("SELECT count(*) FROM sessions"), [(0,)])

    def test_first_signup_takes_over_account_and_tasks(self):
        (uid,) = self.sql("SELECT id FROM users WHERE email='migrated@test.com'")[0]
        self.sql(
            "INSERT INTO tasks (title, description, status, created_at, updated_at, owner_id)"
            " VALUES ('old', '', 'TODO', 'x', 'y', ?)",
            (uid,),
        )
        r = self.new_client().post("/api/auth/signup", json=creds("Migrated@Test.com", PW))
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json(), {"id": uid, "email": "migrated@test.com"})
        self.assertEqual(self.sql("SELECT owner_id FROM tasks"), [(uid,)])
        self.assertEqual(self.sql("SELECT count(*) FROM users"), [(1,)])
        # 이제 로그인할 수 있고, 두 번째 가입은 거부된다.
        login = self.new_client().post("/api/auth/login", json=creds("migrated@test.com"))
        self.assertEqual(login.status_code, 200)
        again = self.new_client().post("/api/auth/signup", json=creds("migrated@test.com", "other-pass1"))
        self.assertEqual(again.status_code, 409)


class LoginTest(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.new_client().post("/api/auth/signup", json=creds())

    def test_login_ok(self):
        c = self.new_client()
        r = c.post("/api/auth/login", json=creds("A@example.com"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(set(r.json()), {"id", "email"})
        self.assertEqual(c.get("/api/auth/me").status_code, 200)

    def test_wrong_password_and_unknown_account_look_the_same(self):
        wrong = self.new_client().post("/api/auth/login", json=creds(password="wrong-pass"))
        unknown = self.new_client().post("/api/auth/login", json=creds("nobody@example.com"))
        self.assertEqual(wrong.status_code, 401)
        self.assertEqual(unknown.status_code, 401)
        self.assertEqual(wrong.json(), unknown.json())
        self.assertNotIn("set-cookie", wrong.headers)

    def test_empty_values_are_422(self):
        for body in (creds(password=""), creds(email=""), {}):
            r = self.new_client().post("/api/auth/login", json=body)
            self.assertEqual(r.status_code, 422)


class SessionTest(ApiTestCase):
    def test_me_requires_login(self):
        c = self.new_client()
        self.assertEqual(c.get("/api/auth/me").status_code, 401)
        c.cookies.set("session", "forged-value")
        self.assertEqual(c.get("/api/auth/me").status_code, 401)

    def test_logout_ends_session_and_deletes_row(self):
        c = self.new_client()
        c.post("/api/auth/signup", json=creds())
        old = c.cookies.get("session")
        self.assertEqual(c.post("/api/auth/logout").status_code, 204)
        self.assertEqual(self.sql("SELECT count(*) FROM sessions"), [(0,)])
        self.assertEqual(c.get("/api/auth/me").status_code, 401)
        # 로그아웃 전의 쿠키 값을 다시 보내도 소용없다.
        c.cookies.set("session", old)
        self.assertEqual(c.get("/api/auth/me").status_code, 401)

    def test_logout_without_login_is_401(self):
        self.assertEqual(self.new_client().post("/api/auth/logout").status_code, 401)

    def test_logout_only_ends_own_session(self):
        a, b = self.new_client(), self.new_client()
        a.post("/api/auth/signup", json=creds())
        b.post("/api/auth/login", json=creds())
        a.post("/api/auth/logout")
        self.assertEqual(b.get("/api/auth/me").status_code, 200)

    def test_expired_session_is_401_and_row_removed(self):
        c = self.new_client()
        c.post("/api/auth/signup", json=creds())
        self.sql("UPDATE sessions SET expires_at='2000-01-01T00:00:00+00:00'")
        self.assertEqual(c.get("/api/auth/me").status_code, 401)
        self.assertEqual(self.sql("SELECT count(*) FROM sessions"), [(0,)])

    def test_unknown_session_hash_is_rejected(self):
        c = self.new_client()
        c.post("/api/auth/signup", json=creds())
        self.sql("UPDATE sessions SET token_hash='0' || substr(token_hash, 2)")
        self.assertEqual(c.get("/api/auth/me").status_code, 401)
