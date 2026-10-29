import json
import os
from datetime import date
from types import SimpleNamespace
from unittest import mock

import anthropic

from app import weekplan
from test_tasks import TasksTestCase

TODAY = date(2026, 10, 28)
FAKE_KEY = "test-only-key"  # 실제 키가 아니다. 네트워크 호출은 모두 mock 이다.
D0, D1, D2, D6 = "2026-10-28", "2026-10-29", "2026-10-30", "2026-11-03"


def reply(text: str, stop_reason: str = "end_turn", block_type: str = "text"):
    return SimpleNamespace(
        stop_reason=stop_reason, content=[SimpleNamespace(type=block_type, text=text)]
    )


def api_error(cls):
    return cls.__new__(cls)


def day(d, ids, note="오늘의 계획"):
    return {"date": d, "ids": list(ids), "note": note}


def answer(*days):
    return json.dumps({"days": list(days)}, ensure_ascii=False)


class WeekplanTest(TasksTestCase):
    def setUp(self):
        super().setUp()
        for p in (
            mock.patch("app.rules.today", return_value=TODAY),
            mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": FAKE_KEY}),
        ):
            p.start()
            self.addCleanup(p.stop)
        self.client, self.uid = self.signup("a@test.com")

    def add(self, client, title, **extra):
        r = client.post("/api/tasks", json={"title": title, "description": "비밀 설명", **extra})
        self.assertEqual(r.status_code, 201, r.text)
        return r.json()["id"]

    def plan(self, result=None, error=None, client=None):
        with mock.patch("app.ai.anthropic.Anthropic") as cls:
            create = cls.return_value.messages.create
            if error is not None:
                create.side_effect = error
            else:
                create.return_value = result
            r = (client or self.client).post("/api/tasks/weekplan")
        self.create_mock, self.cls_mock = create, cls
        return r

    def three(self):
        return [self.add(self.client, f"t{i}") for i in range(3)]

    def test_success_sorted_by_date(self):
        a, b, c = self.three()
        r = self.plan(reply(answer(day(D2, [c]), day(D0, [a, b], "시작"))))
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(
            r.json(),
            {"days": [day(D0, [a, b], "시작"), day(D2, [c])]},
        )

    def test_call_arguments_and_payload(self):
        a = self.add(self.client, "오래된 일", priority="HIGH", due_date="2026-10-01")
        b = self.add(self.client, "나중 일")
        self.plan(reply(answer(day(D0, [a, b]))))
        kw = self.create_mock.call_args.kwargs
        self.assertEqual(kw["model"], "claude-haiku-5-5")
        self.assertEqual(kw["thinking"], {"type": "disabled"})
        self.assertEqual(kw["max_tokens"], 1536)
        self.assertEqual(kw["system"], weekplan.WEEKPLAN_SYSTEM_PROMPT)
        content = kw["messages"][0]["content"]
        self.assertTrue(content.startswith("<today>2026-10-28</today>\n<tasks>\n"))
        lines = content.split("\n")[2:-1]
        self.assertEqual(
            [json.loads(x) for x in lines],
            [
                {"id": a, "title": "오래된 일", "priority": "HIGH",
                 "due_date": "2026-10-01", "overdue": True},
                {"id": b, "title": "나중 일", "priority": "NORMAL",
                 "due_date": None, "overdue": False},
            ],
        )
        self.assertNotIn("비밀 설명", content)
        self.assertNotIn("description", content)

    def test_fenced_json(self):
        a = self.add(self.client, "x")
        text = answer(day(D0, [a]))
        for t in (f"```json\n{text}\n```", f"```\n{text}\n```"):
            with self.subTest(t=t):
                self.assertEqual(self.plan(reply(t)).status_code, 200)

    def test_window_is_today_to_six_days_later(self):
        a, b, c = self.three()
        r = self.plan(reply(answer(day(D0, [a]), day(D6, [b]), day("2026-11-04", [c]))))
        self.assertEqual([d["date"] for d in r.json()["days"]], [D0, D6])

    def test_out_of_window_and_bad_dates_dropped(self):
        a, b, *_ = self.three()
        bad = ["2026-10-27", "2026-11-04", "2026/10/29", "20261029", "2026-02-30", "", "내일"]
        for d in bad:
            with self.subTest(d=d):
                r = self.plan(reply(answer(day(d, [a]), day(D1, [b]))))
                self.assertEqual(r.status_code, 200, r.text)
                self.assertEqual(r.json()["days"], [day(D1, [b])])

    def test_unknown_ids_dropped(self):
        a, *_ = self.three()
        r = self.plan(reply(answer(day(D0, [999, a]), day(D1, [888]))))
        self.assertEqual(r.json()["days"], [day(D0, [a])])

    def test_id_only_on_first_day(self):
        a, b, _ = self.three()
        r = self.plan(reply(answer(day(D0, [a, a]), day(D1, [a, b]))))
        self.assertEqual(r.json()["days"], [day(D0, [a]), day(D1, [b])])

    def test_same_date_merged(self):
        a, b, _ = self.three()
        r = self.plan(reply(answer(day(D0, [a], "첫째"), day(D0, [b], "둘째"))))
        self.assertEqual(r.json()["days"], [day(D0, [a, b], "첫째")])

    def test_due_date_later_day_dropped(self):
        a = self.add(self.client, "마감 있는 일", due_date=D1)
        b = self.add(self.client, "마감 없는 일")
        r = self.plan(reply(answer(day(D1, [b]), day(D2, [a]))))
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["days"], [day(D1, [b])])

    def test_due_day_itself_allowed(self):
        a = self.add(self.client, "x", due_date=D1)
        r = self.plan(reply(answer(day(D1, [a]))))
        self.assertEqual(r.json()["days"], [day(D1, [a])])

    def test_due_today_or_overdue_allowed_today_only(self):
        a = self.add(self.client, "오늘 마감", due_date=D0)
        b = self.add(self.client, "지난 마감", due_date="2026-10-01")
        r = self.plan(reply(answer(day(D0, [a, b]))))
        self.assertEqual(r.json()["days"], [day(D0, [a, b])])
        r = self.plan(reply(answer(day(D0, [b]), day(D1, [a, b]))))
        self.assertEqual(r.json()["days"], [day(D0, [b])])

    def test_dropped_late_id_can_be_placed_on_valid_day(self):
        a = self.add(self.client, "x", due_date=D1)
        r = self.plan(reply(answer(day(D2, [a]), day(D1, [a]))))
        self.assertEqual(r.json()["days"], [day(D1, [a])])

    def test_nothing_left_is_502(self):
        a, *_ = self.three()
        cases = {
            "no days": answer(),
            "all unknown ids": answer(day(D0, [999])),
            "all out of window": answer(day("2026-11-10", [a])),
            "empty ids": answer(day(D0, [])),
        }
        for name, text in cases.items():
            with self.subTest(name):
                r = self.plan(reply(text))
                self.assertEqual(r.status_code, 502, r.text)
                self.assertEqual(r.json()["detail"], "제안 실패")

    def test_invalid_answers_are_502(self):
        a = self.add(self.client, "x")
        ok = day(D0, [a])
        cases = {
            "not json": "안녕하세요",
            "json list": "[1]",
            "empty text": "",
            "missing days": json.dumps({"plan": []}),
            "days not list": json.dumps({"days": {}}),
            "day not dict": answer("x"),
            "missing date": answer({"ids": [a], "note": "n"}),
            "missing ids": answer({"date": D0, "note": "n"}),
            "missing note": answer({"date": D0, "ids": [a]}),
            "date not str": answer({"date": 1, "ids": [a], "note": "n"}),
            "note not str": answer({"date": D0, "ids": [a], "note": 1}),
            "ids not list": answer({"date": D0, "ids": a, "note": "n"}),
            "id str": answer({"date": D0, "ids": [str(a)], "note": "n"}),
            "id bool": answer({"date": D0, "ids": [True], "note": "n"}),
            "id null": answer({"date": D0, "ids": [None], "note": "n"}),
            "one bad day among good": answer(ok, {"date": D1, "ids": "1", "note": "n"}),
        }
        for name, text in cases.items():
            with self.subTest(name):
                r = self.plan(reply(text))
                self.assertEqual(r.status_code, 502, r.text)
                self.assertEqual(r.json()["detail"], "제안 실패")

    def test_truncated_and_non_text_are_502(self):
        a = self.add(self.client, "x")
        for r in (
            reply(answer(day(D0, [a])), stop_reason="max_tokens"),
            reply("{}", block_type="tool_use"),
        ):
            self.assertEqual(self.plan(r).status_code, 502)

    def test_empty_does_not_call_model(self):
        r = self.plan(reply("unused"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"days": []})
        self.cls_mock.assert_not_called()

    def test_only_done_tasks_counts_as_empty(self):
        a = self.add(self.client, "끝난 일")
        self.client.patch(f"/api/tasks/{a}/status", json={"status": "DONE"})
        r = self.plan(reply("unused"))
        self.assertEqual(r.json(), {"days": []})
        self.cls_mock.assert_not_called()

    def test_done_and_other_users_excluded(self):
        mine = self.add(self.client, "내 일")
        done = self.add(self.client, "끝난 일")
        self.client.patch(f"/api/tasks/{done}/status", json={"status": "DONE"})
        other, _ = self.signup("b@test.com")
        theirs = self.add(other, "남의 일")
        self.plan(reply(answer(day(D0, [mine]))))
        content = self.create_mock.call_args.kwargs["messages"][0]["content"]
        sent = [json.loads(x)["id"] for x in content.split("\n")[2:-1]]
        self.assertEqual(sent, [mine])
        self.assertNotIn("남의 일", content)
        self.assertNotIn("끝난 일", content)
        r = self.plan(reply(answer(day(D0, [theirs, done, mine]))))
        self.assertEqual(r.json()["days"], [day(D0, [mine])])

    def test_no_key_is_503_without_call(self):
        self.add(self.client, "x")
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": ""}):
            r = self.plan(reply("unused"))
        self.assertEqual(r.status_code, 503)
        self.assertEqual(r.json()["detail"], "AI 기능 꺼짐")
        self.create_mock.assert_not_called()

    def test_busy_is_503(self):
        self.add(self.client, "x")
        for cls in (anthropic.RateLimitError, anthropic.OverloadedError):
            with self.subTest(cls=cls.__name__):
                r = self.plan(error=api_error(cls))
                self.assertEqual(r.status_code, 503)
                self.assertEqual(r.json()["detail"], "AI 가 바쁩니다. 잠시 후 다시 시도하세요.")

    def test_auth_error_is_503(self):
        self.add(self.client, "x")
        r = self.plan(error=api_error(anthropic.AuthenticationError))
        self.assertEqual(r.status_code, 503)
        self.assertEqual(r.json()["detail"], "AI 기능 꺼짐")

    def test_connection_error_is_502(self):
        self.add(self.client, "x")
        r = self.plan(error=api_error(anthropic.APIConnectionError))
        self.assertEqual(r.status_code, 502)

    def test_requires_login(self):
        with mock.patch("app.ai.anthropic.Anthropic") as cls:
            r = self.new_client().post("/api/tasks/weekplan")
        self.assertEqual(r.status_code, 401)
        cls.assert_not_called()

    def test_does_not_change_db(self):
        a, *_ = self.three()
        before = [tuple(r) for r in self.rows()]
        self.plan(reply(answer(day(D0, [a]))))
        self.assertEqual([tuple(r) for r in self.rows()], before)
