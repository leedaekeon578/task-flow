import json
import os
from datetime import date
from types import SimpleNamespace
from unittest import mock

import anthropic

from app import briefing
from test_tasks import TasksTestCase

TODAY = date(2026, 10, 28)
FAKE_KEY = "test-only-key"  # 실제 키가 아니다. 네트워크 호출은 모두 mock 이다.


def reply(text: str, stop_reason: str = "end_turn", block_type: str = "text"):
    return SimpleNamespace(
        stop_reason=stop_reason, content=[SimpleNamespace(type=block_type, text=text)]
    )


def api_error(cls):
    return cls.__new__(cls)


def answer(top3, later=(), cheer="힘내요!"):
    return json.dumps({"top3": top3, "later": list(later), "cheer": cheer}, ensure_ascii=False)


def top(i, reason="급해요"):
    return {"id": i, "reason": reason}


class BriefingTest(TasksTestCase):
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

    def brief(self, result=None, error=None, client=None):
        with mock.patch("app.ai.anthropic.Anthropic") as cls:
            create = cls.return_value.messages.create
            if error is not None:
                create.side_effect = error
            else:
                create.return_value = result
            r = (client or self.client).post("/api/tasks/briefing")
        self.create_mock, self.cls_mock = create, cls
        return r

    def four(self):
        return [self.add(self.client, f"t{i}") for i in range(4)]

    def test_success(self):
        a, b, c, _ = self.four()
        r = self.brief(reply(answer([top(a), top(b)], [c])))
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(
            r.json(),
            {"top3": [top(a), top(b)], "later": [c], "cheer": "힘내요!"},
        )

    def test_call_arguments_and_payload(self):
        a = self.add(self.client, "오래된 일", priority="HIGH", due_date="2026-10-01")
        b = self.add(self.client, "나중 일")
        self.brief(reply(answer([top(a)], [b])))
        kw = self.create_mock.call_args.kwargs
        self.assertEqual(kw["model"], "claude-haiku-5-5")
        self.assertEqual(kw["thinking"], {"type": "disabled"})
        self.assertEqual(kw["max_tokens"], 1024)
        self.assertEqual(kw["system"], briefing.BRIEFING_SYSTEM_PROMPT)
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
        text = answer([top(a)])
        for t in (f"```json\n{text}\n```", f"```\n{text}\n```"):
            with self.subTest(t=t):
                self.assertEqual(self.brief(reply(t)).status_code, 200)

    def test_unknown_ids_are_dropped(self):
        a, b, *_ = self.four()
        r = self.brief(reply(answer([top(999), top(a)], [b, 888, 777])))
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["top3"], [top(a)])
        self.assertEqual(r.json()["later"], [b])

    def test_top3_keeps_first_three_and_later_excludes_top(self):
        ids = self.four()
        r = self.brief(reply(answer([top(i) for i in ids], ids)))
        body = r.json()
        self.assertEqual([t["id"] for t in body["top3"]], ids[:3])
        self.assertEqual(body["later"], [ids[3]])

    def test_duplicate_ids_collapsed(self):
        a, b, *_ = self.four()
        body = self.brief(reply(answer([top(a), top(a)], [b, b]))).json()
        self.assertEqual(body["top3"], [top(a)])
        self.assertEqual(body["later"], [b])

    def test_all_ids_unknown_is_still_ok(self):
        self.four()
        r = self.brief(reply(answer([top(999)], [888])))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["top3"], [])
        self.assertEqual(r.json()["later"], [])

    def test_invalid_answers_are_502(self):
        a = self.add(self.client, "x")
        cases = {
            "not json": "안녕하세요",
            "json list": "[1, 2]",
            "empty text": "",
            "missing top3": json.dumps({"later": [], "cheer": "c"}),
            "missing later": json.dumps({"top3": [], "cheer": "c"}),
            "missing cheer": json.dumps({"top3": [], "later": []}),
            "blank cheer": answer([], cheer="  "),
            "cheer not str": json.dumps({"top3": [], "later": [], "cheer": 3}),
            "null cheer": json.dumps({"top3": [], "later": [], "cheer": None}),
            "top3 not list": json.dumps({"top3": {}, "later": [], "cheer": "c"}),
            "later not list": json.dumps({"top3": [], "later": "1", "cheer": "c"}),
            "top item not dict": answer([a]),
            "top missing reason": answer([{"id": a}]),
            "top missing id": answer([{"reason": "r"}]),
            "top id str": answer([{"id": str(a), "reason": "r"}]),
            "top id bool": answer([{"id": True, "reason": "r"}]),
            "top reason not str": answer([{"id": a, "reason": 1}]),
            "later id str": answer([], [str(a)]),
            "later id null": answer([], [None]),
        }
        for name, text in cases.items():
            with self.subTest(name):
                r = self.brief(reply(text))
                self.assertEqual(r.status_code, 502, r.text)
                self.assertEqual(r.json()["detail"], "제안 실패")

    def test_truncated_and_non_text_are_502(self):
        a = self.add(self.client, "x")
        for r in (
            reply(answer([top(a)]), stop_reason="max_tokens"),
            reply("{}", block_type="tool_use"),
        ):
            self.assertEqual(self.brief(r).status_code, 502)

    def test_empty_does_not_call_model(self):
        r = self.brief(reply("unused"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"top3": [], "later": [], "cheer": "오늘은 비어 있어요"})
        self.cls_mock.assert_not_called()

    def test_only_done_tasks_counts_as_empty(self):
        a = self.add(self.client, "끝난 일")
        r = self.client.patch(f"/api/tasks/{a}/status", json={"status": "DONE"})
        self.assertEqual(r.status_code, 200)
        r = self.brief(reply("unused"))
        self.assertEqual(r.json()["cheer"], "오늘은 비어 있어요")
        self.cls_mock.assert_not_called()

    def test_done_and_other_users_excluded(self):
        mine = self.add(self.client, "내 일")
        done = self.add(self.client, "끝난 일")
        self.client.patch(f"/api/tasks/{done}/status", json={"status": "DONE"})
        other, _ = self.signup("b@test.com")
        theirs = self.add(other, "남의 일")
        self.brief(reply(answer([top(mine)])))
        content = self.create_mock.call_args.kwargs["messages"][0]["content"]
        sent = [json.loads(x)["id"] for x in content.split("\n")[2:-1]]
        self.assertEqual(sent, [mine])
        self.assertNotIn("남의 일", content)
        self.assertNotIn("끝난 일", content)
        # 남의 id 를 AI 가 돌려줘도 버린다.
        r = self.brief(reply(answer([top(theirs), top(done), top(mine)])))
        self.assertEqual(r.json()["top3"], [top(mine)])

    def test_no_key_is_503_without_call(self):
        self.add(self.client, "x")
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": ""}):
            r = self.brief(reply("unused"))
        self.assertEqual(r.status_code, 503)
        self.assertEqual(r.json()["detail"], "AI 기능 꺼짐")
        self.create_mock.assert_not_called()

    def test_busy_is_503(self):
        self.add(self.client, "x")
        for cls in (anthropic.RateLimitError, anthropic.OverloadedError):
            with self.subTest(cls=cls.__name__):
                r = self.brief(error=api_error(cls))
                self.assertEqual(r.status_code, 503)
                self.assertEqual(r.json()["detail"], "AI 가 바쁩니다. 잠시 후 다시 시도하세요.")

    def test_auth_error_is_503(self):
        self.add(self.client, "x")
        r = self.brief(error=api_error(anthropic.AuthenticationError))
        self.assertEqual(r.status_code, 503)
        self.assertEqual(r.json()["detail"], "AI 기능 꺼짐")

    def test_connection_error_is_502(self):
        self.add(self.client, "x")
        r = self.brief(error=api_error(anthropic.APIConnectionError))
        self.assertEqual(r.status_code, 502)

    def test_requires_login(self):
        with mock.patch("app.ai.anthropic.Anthropic") as cls:
            r = self.new_client().post("/api/tasks/briefing")
        self.assertEqual(r.status_code, 401)
        cls.assert_not_called()

    def test_does_not_change_db(self):
        self.four()
        before = self.rows()
        self.brief(reply(answer([top(1)])))
        self.assertEqual([tuple(r) for r in self.rows()], [tuple(r) for r in before])
