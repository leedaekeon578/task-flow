from support import ApiTestCase

PW = "correct-horse"


class TasksTestCase(ApiTestCase):
    def signup(self, email: str):
        c = self.new_client()
        r = c.post("/api/auth/signup", json={"email": email, "password": PW})
        self.assertEqual(r.status_code, 201)
        return c, r.json()["id"]

    def make_task(self, client, title="t", description="d") -> dict:
        r = client.post("/api/tasks", json={"title": title, "description": description})
        self.assertEqual(r.status_code, 201)
        return r.json()

    def rows(self):
        return self.sql("SELECT * FROM tasks ORDER BY id")


class UnauthenticatedTest(TasksTestCase):
    def requests(self, c, task_id):
        body = {"title": "x", "description": ""}
        return {
            "list": c.get("/api/tasks"),
            "create": c.post("/api/tasks", json=body),
            "update": c.patch(f"/api/tasks/{task_id}", json=body),
            "status": c.patch(f"/api/tasks/{task_id}/status", json={"status": "DONE"}),
            "delete": c.delete(f"/api/tasks/{task_id}"),
        }

    def test_all_five_are_401_and_change_nothing(self):
        owner, _ = self.signup("a@example.com")
        task = self.make_task(owner)
        before = self.rows()
        for name, r in self.requests(self.new_client(), task["id"]).items():
            with self.subTest(api=name):
                self.assertEqual(r.status_code, 401)
        self.assertEqual(self.rows(), before)

    def test_401_comes_before_lookup_and_validation(self):
        # 있는 카드든 없는 카드든, 본문이 틀렸든 같은 401 이다. (남의 카드 존재 여부를 알려 주지 않는다)
        c = self.new_client()
        owner, _ = self.signup("a@example.com")
        task = self.make_task(owner)
        existing = c.patch(f"/api/tasks/{task['id']}/status", json={"status": "DONE"})
        missing = c.patch("/api/tasks/9999/status", json={"status": "DONE"})
        bad_body = c.patch(f"/api/tasks/{task['id']}/status", json={"status": "NOPE"})
        self.assertEqual({existing.status_code, missing.status_code, bad_body.status_code}, {401})
        self.assertEqual(existing.json(), missing.json())
        self.assertEqual(c.post("/api/tasks", json={"title": "  "}).status_code, 401)

    def test_expired_session_is_401(self):
        c, _ = self.signup("a@example.com")
        self.sql("UPDATE sessions SET expires_at='2000-01-01T00:00:00+00:00'")
        self.assertEqual(c.get("/api/tasks").status_code, 401)

    def test_after_logout_is_401(self):
        c, _ = self.signup("a@example.com")
        c.post("/api/auth/logout")
        self.assertEqual(c.get("/api/tasks").status_code, 401)


class OwnerIsolationTest(TasksTestCase):
    def test_list_returns_only_my_tasks(self):
        a, _ = self.signup("a@example.com")
        b, _ = self.signup("b@example.com")
        a1, a2 = self.make_task(a, "a1"), self.make_task(a, "a2")
        b1 = self.make_task(b, "b1")
        self.assertEqual([t["id"] for t in a.get("/api/tasks").json()], [a1["id"], a2["id"]])
        self.assertEqual([t["id"] for t in b.get("/api/tasks").json()], [b1["id"]])

    def test_no_tasks_is_empty_list_not_error(self):
        c, _ = self.signup("new@example.com")
        r = c.get("/api/tasks")
        self.assertEqual((r.status_code, r.json()), (200, []))

    def test_create_sets_owner_from_session_and_ignores_body(self):
        a, a_id = self.signup("a@example.com")
        _, b_id = self.signup("b@example.com")
        r = a.post("/api/tasks", json={"title": "mine", "description": "", "owner_id": b_id})
        self.assertEqual(r.status_code, 201)
        self.assertNotIn("owner_id", r.json())
        self.assertEqual(self.sql("SELECT owner_id FROM tasks WHERE id=?", (r.json()["id"],)), [(a_id,)])

    def test_other_users_task_is_404_same_as_missing_and_unchanged(self):
        a, _ = self.signup("a@example.com")
        b, _ = self.signup("b@example.com")
        task = self.make_task(a, "secret", "desc")
        before = self.rows()
        body = {"title": "hacked", "description": "x"}
        attempts = {
            "update": lambda c, i: c.patch(f"/api/tasks/{i}", json=body),
            "status": lambda c, i: c.patch(f"/api/tasks/{i}/status", json={"status": "DONE"}),
            "delete": lambda c, i: c.delete(f"/api/tasks/{i}"),
        }
        for name, call in attempts.items():
            with self.subTest(api=name):
                other = call(b, task["id"])
                missing = call(b, 9999)
                self.assertEqual(other.status_code, 404)
                self.assertEqual(missing.status_code, 404)
                self.assertEqual(other.content, missing.content)
        self.assertEqual(self.rows(), before)
        self.assertEqual(a.get("/api/tasks").json()[0]["title"], "secret")

    def test_owner_can_still_do_everything(self):
        a, _ = self.signup("a@example.com")
        task = self.make_task(a, "t")
        self.assertEqual(task["status"], "TODO")
        r = a.patch(f"/api/tasks/{task['id']}/status", json={"status": "DONE"})
        self.assertEqual((r.status_code, r.json()["status"]), (200, "DONE"))
        r = a.patch(f"/api/tasks/{task['id']}", json={"title": "t2", "description": "d2"})
        self.assertEqual((r.status_code, r.json()["title"], r.json()["status"]), (200, "t2", "DONE"))
        self.assertEqual(a.delete(f"/api/tasks/{task['id']}").status_code, 204)
        self.assertEqual(a.delete(f"/api/tasks/{task['id']}").status_code, 404)
        self.assertEqual(a.get("/api/tasks").json(), [])

    def test_validation_still_applies(self):
        a, _ = self.signup("a@example.com")
        self.assertEqual(a.post("/api/tasks", json={"title": "   "}).status_code, 422)
        task = self.make_task(a)
        self.assertEqual(
            a.patch(f"/api/tasks/{task['id']}/status", json={"status": "NOPE"}).status_code, 422
        )

    def test_owner_never_changes(self):
        a, a_id = self.signup("a@example.com")
        task = self.make_task(a)
        a.patch(f"/api/tasks/{task['id']}", json={"title": "n", "description": "", "owner_id": 999})
        a.patch(f"/api/tasks/{task['id']}/status", json={"status": "DONE", "owner_id": 999})
        self.assertEqual(self.sql("SELECT owner_id FROM tasks"), [(a_id,)])


class MigratedTasksTest(TasksTestCase):
    def test_first_signup_sees_existing_tasks_and_others_do_not(self):
        (uid,) = self.sql("SELECT id FROM users WHERE email='migrated@test.com'")[0]
        for title in ("old1", "old2"):
            self.sql(
                "INSERT INTO tasks (title, description, status, created_at, updated_at, owner_id)"
                " VALUES (?, '', 'TODO', 'x', 'y', ?)",
                (title, uid),
            )
        other, _ = self.signup("other@example.com")
        self.assertEqual(other.get("/api/tasks").json(), [])
        heir, heir_id = self.signup("migrated@test.com")
        self.assertEqual(heir_id, uid)
        self.assertEqual([t["title"] for t in heir.get("/api/tasks").json()], ["old1", "old2"])
