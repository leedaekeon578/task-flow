from datetime import UTC, date, datetime
from unittest import TestCase, mock

from app import rules
from test_tasks import TasksTestCase

TODAY = date(2026, 10, 27)


class TodayTest(TestCase):
    def fake_now(self, utc: datetime):
        class FakeDatetime(datetime):
            @classmethod
            def now(cls, tz=None):
                return utc.astimezone(tz)

        return mock.patch("app.rules.datetime", FakeDatetime)

    def test_today_is_korea_date_from_one_place(self):
        # UTC 15:00 이 한국 시간 자정이다.
        with self.fake_now(datetime(2026, 10, 26, 14, 59, tzinfo=UTC)):
            self.assertEqual(rules.today(), date(2026, 10, 26))
        with self.fake_now(datetime(2026, 10, 26, 15, 0, tzinfo=UTC)):
            self.assertEqual(rules.today(), date(2026, 10, 27))


class PriorityDueTestCase(TasksTestCase):
    def setUp(self):
        super().setUp()
        patch = mock.patch("app.rules.today", return_value=TODAY)
        patch.start()
        self.addCleanup(patch.stop)

    def make(self, client, title="t", **extra) -> dict:
        r = client.post("/api/tasks", json={"title": title, **extra})
        self.assertEqual(r.status_code, 201, r.text)
        return r.json()

    def row(self, task_id):
        return self.sql(
            "SELECT title, description, status, priority, due_date, updated_at FROM tasks WHERE id=?",
            (task_id,),
        )[0]

    def patch(self, client, task_id, **body):
        return client.patch(f"/api/tasks/{task_id}", json=body)


class CreateTest(PriorityDueTestCase):
    def test_defaults_when_omitted(self):
        a, _ = self.signup("a@example.com")
        t = self.make(a)
        self.assertEqual((t["priority"], t["due_date"], t["overdue"]), ("NORMAL", None, False))
        self.assertNotIn("owner_id", t)

    def test_accepts_both_fields_including_past_date(self):
        a, _ = self.signup("a@example.com")
        t = self.make(a, priority="HIGH", due_date="2026-10-01")
        self.assertEqual((t["priority"], t["due_date"], t["overdue"]), ("HIGH", "2026-10-01", True))
        self.assertEqual(self.row(t["id"])[3:5], ("HIGH", "2026-10-01"))

    def test_invalid_values_are_422_and_not_saved(self):
        a, _ = self.signup("a@example.com")
        bad = [
            {"priority": "URGENT"},
            {"priority": "high"},
            {"priority": None},
            {"due_date": "2026-02-30"},
            {"due_date": "2026/10/01"},
            {"due_date": "2026-1-5"},
            {"due_date": "2026-10-01T00:00:00"},
            {"due_date": ""},
            {"due_date": 20261001},
        ]
        for extra in bad:
            with self.subTest(extra=extra):
                r = a.post("/api/tasks", json={"title": "x", **extra})
                self.assertEqual(r.status_code, 422)
        self.assertEqual(self.rows(), [])


class UpdateTest(PriorityDueTestCase):
    def setUp(self):
        super().setUp()
        self.a, _ = self.signup("a@example.com")
        self.task = self.make(self.a, "t", description="d", priority="HIGH", due_date="2026-12-01")
        self.id = self.task["id"]

    def test_title_only_keeps_priority_and_due_date(self):
        # 제목만 보내도 새 필드가 기본값으로 덮어써지지 않는다. (IMPACT-ANALYSIS 2-2 첫째)
        r = self.patch(self.a, self.id, title="new")
        self.assertEqual(r.status_code, 200)
        self.assertEqual((r.json()["priority"], r.json()["due_date"]), ("HIGH", "2026-12-01"))
        self.assertEqual(self.row(self.id)[:5], ("new", "", "TODO", "HIGH", "2026-12-01"))

    def test_title_and_description_only_keeps_new_fields(self):
        self.patch(self.a, self.id, title="n", description="x")
        self.assertEqual(self.row(self.id)[3:5], ("HIGH", "2026-12-01"))

    def test_missing_description_still_blanks_it_as_before(self):
        # 제목 · 설명 처리는 지금 동작 그대로: 설명을 안 보내면 빈 설명.
        self.patch(self.a, self.id, title="n")
        self.assertEqual(self.row(self.id)[1], "")

    def test_change_only_priority_or_due_date_is_saved(self):
        # 제목 · 설명이 같아도 새 필드만 바뀐 요청이 "변경 없음"으로 무시되지 않는다.
        r = self.patch(self.a, self.id, title="t", description="d", priority="LOW")
        self.assertEqual(r.json()["priority"], "LOW")
        self.assertEqual(self.row(self.id)[3:5], ("LOW", "2026-12-01"))
        r = self.patch(self.a, self.id, title="t", description="d", due_date="2026-12-31")
        self.assertEqual(r.json()["due_date"], "2026-12-31")
        self.assertEqual(self.row(self.id)[3:5], ("LOW", "2026-12-31"))

    def test_null_due_date_clears_but_null_priority_is_422(self):
        r = self.patch(self.a, self.id, title="t", description="d", due_date=None)
        self.assertEqual((r.status_code, r.json()["due_date"]), (200, None))
        before = self.rows()
        r = self.patch(self.a, self.id, title="t", description="d", priority=None)
        self.assertEqual(r.status_code, 422)
        self.assertEqual(self.rows(), before)

    def test_invalid_values_are_422_and_change_nothing(self):
        before = self.rows()
        for extra in ({"priority": "URGENT"}, {"due_date": "2026-02-30"}, {"due_date": "abc"}):
            with self.subTest(extra=extra):
                r = self.patch(self.a, self.id, title="changed", description="c", **extra)
                self.assertEqual(r.status_code, 422)
        self.assertEqual(self.rows(), before)

    def test_past_due_date_is_allowed(self):
        r = self.patch(self.a, self.id, title="t", description="d", due_date="2000-01-01")
        self.assertEqual((r.status_code, r.json()["overdue"]), (200, True))

    def test_updated_at_changes_only_when_one_of_four_values_changes(self):
        # 시계에 기대지 않는다. 요청 전에 updated_at 을 SENTINEL 로 심고, 요청 뒤 값이 남았는지 본다.
        def updated_at():
            return self.row(self.id)[5]

        def plant():
            self.sql("UPDATE tasks SET updated_at = 'SENTINEL' WHERE id = ?", (self.id,))

        # 같은 값 · 안 보낸 값 → 그대로
        for body in (
            {"title": "t", "description": "d"},
            {"title": "t", "description": "d", "priority": "HIGH", "due_date": "2026-12-01"},
        ):
            with self.subTest(unchanged=body):
                plant()
                self.patch(self.a, self.id, **body)
                self.assertEqual(updated_at(), "SENTINEL")
        # 네 필드 각각이 바뀔 때마다 갱신 (값은 누적된다)
        bodies = [
            {"title": "t2", "description": "d"},
            {"title": "t2", "description": "d2"},
            {"title": "t2", "description": "d2", "priority": "LOW"},
            {"title": "t2", "description": "d2", "priority": "LOW", "due_date": None},
        ]
        for body in bodies:
            with self.subTest(changed=body):
                plant()
                self.patch(self.a, self.id, **body)
                self.assertNotEqual(updated_at(), "SENTINEL")

    def test_status_is_not_changed_by_update(self):
        self.a.patch(f"/api/tasks/{self.id}/status", json={"status": "DONE"})
        self.patch(self.a, self.id, title="n", priority="LOW")
        self.assertEqual(self.row(self.id)[2], "DONE")


class StatusChangeTest(PriorityDueTestCase):
    def test_does_not_touch_new_fields_and_returns_them(self):
        a, _ = self.signup("a@example.com")
        t = self.make(a, priority="HIGH", due_date="2026-10-01")
        # 두 필드를 보내도 받지 않는다.
        r = a.patch(
            f"/api/tasks/{t['id']}/status",
            json={"status": "DONE", "priority": "LOW", "due_date": "2030-01-01"},
        )
        body = r.json()
        self.assertEqual((body["status"], body["priority"], body["due_date"]), ("DONE", "HIGH", "2026-10-01"))
        self.assertFalse(body["overdue"])  # 완료는 기한 초과가 아니다.
        self.assertEqual(self.row(t["id"])[3:5], ("HIGH", "2026-10-01"))
        r = a.patch(f"/api/tasks/{t['id']}/status", json={"status": "TODO"})
        self.assertTrue(r.json()["overdue"])

    def test_same_status_keeps_updated_at(self):
        a, _ = self.signup("a@example.com")
        t = self.make(a)
        # 시계에 기대지 않고 SENTINEL 을 심어, 같은 상태면 그 값이 남는지 본다.
        self.sql("UPDATE tasks SET updated_at = 'SENTINEL' WHERE id = ?", (t["id"],))
        a.patch(f"/api/tasks/{t['id']}/status", json={"status": "TODO"})
        self.assertEqual(self.row(t["id"])[5], "SENTINEL")
        # 다른 상태로 바꾸면 갱신된다.
        a.patch(f"/api/tasks/{t['id']}/status", json={"status": "DONE"})
        self.assertNotEqual(self.row(t["id"])[5], "SENTINEL")


class OverdueTest(PriorityDueTestCase):
    def test_boundaries(self):
        a, _ = self.signup("a@example.com")
        cases = {
            "2026-10-26": True,  # 어제
            "2026-10-27": False,  # 오늘 당일
            "2026-10-28": False,  # 내일
            None: False,
        }
        for due, expected in cases.items():
            with self.subTest(due=due):
                t = self.make(a, **({"due_date": due} if due else {}))
                self.assertEqual(t["overdue"], expected)

    def test_done_is_never_overdue_in_list(self):
        a, _ = self.signup("a@example.com")
        t = self.make(a, due_date="2026-10-01")
        a.patch(f"/api/tasks/{t['id']}/status", json={"status": "DONE"})
        self.assertFalse(a.get("/api/tasks").json()[0]["overdue"])

    def test_overdue_is_not_stored(self):
        a, _ = self.signup("a@example.com")
        self.make(a, due_date="2026-10-01")
        cols = [r[1] for r in self.sql("PRAGMA table_info(tasks)")]
        self.assertNotIn("overdue", cols)


class SortTest(PriorityDueTestCase):
    def ids(self, client, status=None):
        tasks = client.get("/api/tasks").json()
        return [t["id"] for t in tasks if status is None or t["status"] == status]

    def test_order_overdue_priority_due_then_id(self):
        a, _ = self.signup("a@example.com")
        # 일부러 정렬과 다른 순서로 만든다.
        no_date_low = self.make(a, "no_date_low", priority="LOW")["id"]
        no_date_normal = self.make(a, "no_date_normal")["id"]
        no_date_normal2 = self.make(a, "no_date_normal2")["id"]
        far_normal = self.make(a, "far_normal", due_date="2026-12-31")["id"]
        near_normal = self.make(a, "near_normal", due_date="2026-11-01")["id"]
        high_no_date = self.make(a, "high_no_date", priority="HIGH")["id"]
        high_dated = self.make(a, "high_dated", priority="HIGH", due_date="2026-11-30")["id"]
        today_high = self.make(a, "today_high", priority="HIGH", due_date="2026-10-27")["id"]
        overdue_low = self.make(a, "overdue_low", priority="LOW", due_date="2026-09-01")["id"]
        overdue_high_old = self.make(a, "overdue_high_old", priority="HIGH", due_date="2026-08-01")["id"]
        overdue_high_new = self.make(a, "overdue_high_new", priority="HIGH", due_date="2026-10-20")["id"]
        self.assertEqual(
            self.ids(a),
            [
                # 기한 초과: 우선순위 → 가까운(=더 이른) 마감일
                overdue_high_old,
                overdue_high_new,
                overdue_low,
                # 그 밖: HIGH(마감일 있는 것 → 없는 것, 오늘 마감도 여기), NORMAL, LOW
                today_high,
                high_dated,
                high_no_date,
                near_normal,
                far_normal,
                no_date_normal,
                no_date_normal2,
                no_date_low,
            ],
        )

    def test_done_overdue_card_sorts_as_not_overdue(self):
        a, _ = self.signup("a@example.com")
        done_old = self.make(a, "done_old", priority="LOW", due_date="2026-01-01")["id"]
        normal = self.make(a, "normal")["id"]
        a.patch(f"/api/tasks/{done_old}/status", json={"status": "DONE"})
        # 완료라 기한 초과가 아니므로 LOW 가 NORMAL 보다 뒤다.
        self.assertEqual(self.ids(a), [normal, done_old])

    def test_order_inside_each_column(self):
        a, _ = self.signup("a@example.com")
        x = self.make(a, "x")["id"]
        y = self.make(a, "y", priority="HIGH")["id"]
        z = self.make(a, "z", priority="HIGH")["id"]
        w = self.make(a, "w", due_date="2026-01-01")["id"]
        for i in (x, y):
            a.patch(f"/api/tasks/{i}/status", json={"status": "IN_PROGRESS"})
        self.assertEqual(self.ids(a, "TODO"), [w, z])
        self.assertEqual(self.ids(a, "IN_PROGRESS"), [y, x])

    def test_order_follows_edits(self):
        a, _ = self.signup("a@example.com")
        first = self.make(a, "first")["id"]
        second = self.make(a, "second")["id"]
        self.assertEqual(self.ids(a), [first, second])
        self.patch(a, second, title="second", priority="HIGH")
        self.assertEqual(self.ids(a), [second, first])


class RegressionTest(PriorityDueTestCase):
    def test_other_users_cards_never_mix_in_list_or_sort(self):
        a, _ = self.signup("a@example.com")
        b, _ = self.signup("b@example.com")
        a1 = self.make(a, "a1")["id"]
        b_high = self.make(b, "b_high", priority="HIGH", due_date="2026-01-01")["id"]
        a2 = self.make(a, "a2", priority="HIGH")["id"]
        self.assertEqual([t["id"] for t in a.get("/api/tasks").json()], [a2, a1])
        self.assertEqual([t["id"] for t in b.get("/api/tasks").json()], [b_high])

    def test_other_users_card_update_is_404_and_unchanged(self):
        a, _ = self.signup("a@example.com")
        b, _ = self.signup("b@example.com")
        t = self.make(a, priority="HIGH", due_date="2026-12-01")
        before = self.rows()
        other = b.patch(f"/api/tasks/{t['id']}", json={"title": "x", "priority": "LOW", "due_date": None})
        missing = b.patch("/api/tasks/9999", json={"title": "x", "priority": "LOW", "due_date": None})
        self.assertEqual((other.status_code, other.content), (404, missing.content))
        self.assertEqual(self.rows(), before)

    def test_old_cards_with_default_new_fields_work_everywhere(self):
        # 새 열의 기본값(NORMAL · NULL)만 가진 행. 마이그레이션 직후의 기존 카드와 같다.
        (uid,) = self.sql("SELECT id FROM users WHERE email='migrated@test.com'")[0]
        self.sql(
            "INSERT INTO tasks (title, description, status, created_at, updated_at, owner_id)"
            " VALUES ('old', '', 'TODO', 'x', 'y', ?)",
            (uid,),
        )
        heir, _ = self.signup("migrated@test.com")
        (card,) = heir.get("/api/tasks").json()
        self.assertEqual((card["priority"], card["due_date"], card["overdue"]), ("NORMAL", None, False))
        r = heir.patch(f"/api/tasks/{card['id']}/status", json={"status": "DONE"})
        self.assertEqual(r.status_code, 200)
        r = self.patch(heir, card["id"], title="old2")
        self.assertEqual((r.status_code, r.json()["priority"], r.json()["due_date"]), (200, "NORMAL", None))

    def test_requests_without_new_fields_still_work(self):
        a, _ = self.signup("a@example.com")
        t = a.post("/api/tasks", json={"title": "t", "description": "d"}).json()
        r = a.patch(f"/api/tasks/{t['id']}", json={"title": "t2", "description": "d2"})
        self.assertEqual((r.status_code, r.json()["title"]), (200, "t2"))

    def test_unauthenticated_new_apis_still_401(self):
        c = self.new_client()
        self.assertEqual(c.get("/api/tasks").status_code, 401)
        self.assertEqual(c.post("/api/tasks", json={"title": "x", "priority": "HIGH"}).status_code, 401)
        self.assertEqual(c.patch("/api/tasks/1", json={"title": "x", "priority": None}).status_code, 401)
