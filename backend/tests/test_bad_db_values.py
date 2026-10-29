import json
import os
from datetime import date
from types import SimpleNamespace
from unittest import mock

from test_tasks import TasksTestCase

TODAY = date(2026, 10, 28)

# priority · due_date 는 DB 에 CHECK 가 없어 이상한 값이 들어 있을 수 있다. (0003_priority_due.py)
BAD_VALUES = {
    "bad due_date format": ("due_date", "2026/10/30"),
    "impossible due_date": ("due_date", "2026-02-30"),
    "garbage due_date": ("due_date", "내일"),
    "empty due_date": ("due_date", ""),
    "lowercase priority": ("priority", "high"),
    "unknown priority": ("priority", "URGENT"),
    "empty priority": ("priority", ""),
}


class BadDbValuesTest(TasksTestCase):
    def setUp(self):
        super().setUp()
        for p in (
            mock.patch("app.rules.today", return_value=TODAY),
            mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-only-key"}),
        ):
            p.start()
            self.addCleanup(p.stop)
        self.client, _ = self.signup("a@test.com")
        self.good = self.make_task(self.client, "정상")["id"]
        self.bad = self.make_task(self.client, "이상한 값")["id"]

    def corrupt(self, column, value):
        # 부분 테스트마다 정상 값으로 되돌린 뒤 한 칸만 망가뜨린다.
        self.sql(
            "UPDATE tasks SET priority = 'NORMAL', due_date = NULL WHERE id = ?", (self.bad,)
        )
        self.sql(f"UPDATE tasks SET {column} = ? WHERE id = ?", (value, self.bad))

    def test_list_survives_bad_values(self):
        for name, (column, value) in BAD_VALUES.items():
            with self.subTest(name):
                self.corrupt(column, value)
                r = self.client.get("/api/tasks")
                self.assertEqual(r.status_code, 200, r.text)
                self.assertEqual({t["id"] for t in r.json()}, {self.good, self.bad})

    def test_briefing_survives_bad_values(self):
        text = json.dumps({"top3": [], "later": [], "cheer": "힘내요"})
        for name, (column, value) in BAD_VALUES.items():
            with self.subTest(name):
                self.corrupt(column, value)
                with mock.patch("app.ai.anthropic.Anthropic") as cls:
                    cls.return_value.messages.create.return_value = SimpleNamespace(
                        stop_reason="end_turn",
                        content=[SimpleNamespace(type="text", text=text)],
                    )
                    r = self.client.post("/api/tasks/briefing")
                self.assertEqual(r.status_code, 200, r.text)
