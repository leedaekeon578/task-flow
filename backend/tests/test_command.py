import json
import os
from datetime import date
from types import SimpleNamespace
from unittest import mock

import anthropic

from app import command
from test_tasks import TasksTestCase

TODAY = date(2026, 10, 28)
FAKE_KEY = "test-only-key"  # 실제 키가 아니다. 네트워크 호출은 모두 mock 이다.
NOT_UNDERSTOOD = "무엇을 하라는 건지 이해하지 못했어요. 다시 말씀해 주세요."


def reply(text: str, stop_reason: str = "end_turn", block_type: str = "text"):
    return SimpleNamespace(
        stop_reason=stop_reason, content=[SimpleNamespace(type=block_type, text=text)]
    )


def api_error(cls):
    return cls.__new__(cls)


def answer(actions, ask=None):
    return json.dumps({"actions": actions, "ask": ask}, ensure_ascii=False)


def add(title="새 일", priority="HIGH", due_date=None):
    return {"kind": "add", "id": None, "title": title, "priority": priority, "due_date": due_date}


def due(i, due_date="2026-11-05"):
    return {"kind": "due", "id": i, "due_date": due_date}


def done(i):
    return {"kind": "done", "id": i}


def out_add(title="새 일", priority="HIGH", due_date=None):
    return {"kind": "add", "id": None, "title": title, "priority": priority, "due_date": due_date}


def out_due(i, title, due_date="2026-11-05"):
    return {"kind": "due", "id": i, "title": title, "priority": None, "due_date": due_date}


def out_done(i, title):
    return {"kind": "done", "id": i, "title": title, "priority": None, "due_date": None}


class CommandTest(TasksTestCase):
    def setUp(self):
        super().setUp()
        for p in (
            mock.patch("app.rules.today", return_value=TODAY),
            mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": FAKE_KEY}),
        ):
            p.start()
            self.addCleanup(p.stop)
        self.client, self.uid = self.signup("a@test.com")

    def add_task(self, client, title, **extra):
        r = client.post("/api/tasks", json={"title": title, "description": "비밀 설명", **extra})
        self.assertEqual(r.status_code, 201, r.text)
        return r.json()["id"]

    def run_command(self, result=None, error=None, client=None, text="문장"):
        with mock.patch("app.ai.anthropic.Anthropic") as cls:
            create = cls.return_value.messages.create
            if error is not None:
                create.side_effect = error
            else:
                create.return_value = result
            r = (client or self.client).post("/api/tasks/command", json={"text": text})
        self.create_mock, self.cls_mock = create, cls
        return r

    def test_success_mixed_actions(self):
        a = self.add_task(self.client, "보고서")
        b = self.add_task(self.client, "장보기")
        r = self.run_command(
            reply(answer([add("청소", "LOW", "2026-11-01"), due(a), done(b)]))
        )
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(
            r.json(),
            {
                "actions": [
                    out_add("청소", "LOW", "2026-11-01"),
                    out_due(a, "보고서"),
                    out_done(b, "장보기"),
                ],
                "ask": None,
            },
        )

    def test_call_arguments_and_payload(self):
        a = self.add_task(self.client, "오래된 일", priority="HIGH", due_date="2026-10-01")
        b = self.add_task(self.client, "나중 일")
        self.run_command(reply(answer([done(a)])), text="오래된 일 끝냈어")
        kw = self.create_mock.call_args.kwargs
        self.assertEqual(kw["model"], "claude-haiku-5-5")
        self.assertEqual(kw["thinking"], {"type": "disabled"})
        self.assertEqual(kw["max_tokens"], 1024)
        self.assertEqual(kw["system"], command.COMMAND_SYSTEM_PROMPT)
        content = kw["messages"][0]["content"]
        self.assertTrue(content.startswith("<today>2026-10-28</today>\n<tasks>\n"))
        self.assertTrue(content.endswith("</tasks>\n<command>오래된 일 끝냈어</command>"))
        lines = content.split("\n")[2:-2]
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
        text = answer([add()])
        for t in (f"```json\n{text}\n```", f"```\n{text}\n```"):
            with self.subTest(t=t):
                self.assertEqual(self.run_command(reply(t)).status_code, 200)

    def test_unknown_other_user_and_done_ids_are_dropped(self):
        mine = self.add_task(self.client, "내 일")
        finished = self.add_task(self.client, "끝난 일")
        self.client.patch(f"/api/tasks/{finished}/status", json={"status": "DONE"})
        other, _ = self.signup("b@test.com")
        theirs = self.add_task(other, "남의 일")
        r = self.run_command(
            reply(answer([done(999), done(theirs), done(finished), due(theirs), done(mine)]))
        )
        self.assertEqual(r.json()["actions"], [out_done(mine, "내 일")])
        content = self.create_mock.call_args.kwargs["messages"][0]["content"]
        self.assertNotIn("남의 일", content)
        self.assertNotIn("끝난 일", content)

    def test_invalid_dates_are_dropped(self):
        a = self.add_task(self.client, "x")
        bad = ["2026-02-30", "내일", "2026/11/05", "", 20261105, None]
        for d in bad:
            with self.subTest(d=d):
                r = self.run_command(reply(answer([due(a, d)])))
                self.assertEqual(r.json(), {"actions": [], "ask": NOT_UNDERSTOOD})
        # add 는 규칙 밖 날짜만 null 로 둔다.
        r = self.run_command(reply(answer([add(due_date="2026-02-30")])))
        self.assertEqual(r.json()["actions"], [out_add(due_date=None)])

    def test_past_date_is_kept(self):
        a = self.add_task(self.client, "x")
        r = self.run_command(reply(answer([due(a, "2026-01-01")])))
        self.assertEqual(r.json()["actions"][0]["due_date"], "2026-01-01")

    def test_add_priority_defaults_to_normal(self):
        for p in (None, "URGENT", "high", 3, ""):
            with self.subTest(p=p):
                r = self.run_command(reply(answer([add(priority=p)])))
                self.assertEqual(r.json()["actions"][0]["priority"], "NORMAL")
        raw = {"kind": "add", "title": "키 없음"}
        r = self.run_command(reply(answer([raw])))
        self.assertEqual(r.json()["actions"], [out_add("키 없음", "NORMAL", None)])

    def test_add_with_bad_title_is_dropped(self):
        for t in ("", "   ", None, 3, "가" * 101):
            with self.subTest(t=t):
                r = self.run_command(reply(answer([add(title=t)])))
                self.assertEqual(r.json(), {"actions": [], "ask": NOT_UNDERSTOOD})
        r = self.run_command(reply(answer([add(title="가" * 100)])))
        self.assertEqual(len(r.json()["actions"]), 1)

    def test_add_ignores_model_id(self):
        raw = {**add(), "id": 5}
        self.assertIsNone(self.run_command(reply(answer([raw]))).json()["actions"][0]["id"])

    def test_title_of_existing_cards_comes_from_db(self):
        a = self.add_task(self.client, "진짜 제목")
        r = self.run_command(reply(answer([{"kind": "done", "id": a, "title": "가짜 제목"}])))
        self.assertEqual(r.json()["actions"], [out_done(a, "진짜 제목")])

    def test_nothing_left_returns_model_ask_or_fixed_sentence(self):
        r = self.run_command(reply(answer([done(999)], ask="어느 카드인가요?")))
        self.assertEqual(r.json(), {"actions": [], "ask": "어느 카드인가요?"})
        for ask in (None, "", "  "):
            with self.subTest(ask=ask):
                r = self.run_command(reply(answer([], ask=ask)))
                self.assertEqual(r.json(), {"actions": [], "ask": NOT_UNDERSTOOD})

    def test_ask_is_null_when_actions_remain(self):
        r = self.run_command(reply(answer([add()], ask="무시될 문장")))
        self.assertIsNone(r.json()["ask"])

    def test_duplicates_collapsed(self):
        a = self.add_task(self.client, "x")
        r = self.run_command(reply(answer([done(a), done(a), add("새"), add("새"), due(a)])))
        self.assertEqual(
            [(x["kind"], x["id"]) for x in r.json()["actions"]],
            [("done", a), ("add", None), ("due", a)],
        )

    def test_invalid_answers_are_502(self):
        a = self.add_task(self.client, "x")
        cases = {
            "not json": "안녕하세요",
            "json list": "[1, 2]",
            "empty text": "",
            "missing actions": json.dumps({"ask": None}),
            "actions not list": json.dumps({"actions": {}, "ask": None}),
            "ask not str": json.dumps({"actions": [], "ask": 3}),
            "item not dict": answer([a]),
            "unknown kind": answer([{"kind": "delete", "id": a}]),
            "missing kind": answer([{"id": a}]),
            "done id str": answer([{"kind": "done", "id": str(a)}]),
            "done id bool": answer([{"kind": "done", "id": True}]),
            "done id missing": answer([{"kind": "done"}]),
            "due id null": answer([{"kind": "due", "id": None, "due_date": "2026-11-05"}]),
        }
        for name, text in cases.items():
            with self.subTest(name):
                r = self.run_command(reply(text))
                self.assertEqual(r.status_code, 502, r.text)
                self.assertEqual(r.json()["detail"], "제안 실패")

    def test_truncated_and_non_text_are_502(self):
        for r in (
            reply(answer([add()]), stop_reason="max_tokens"),
            reply("{}", block_type="tool_use"),
        ):
            self.assertEqual(self.run_command(r).status_code, 502)

    def test_empty_list_still_calls_model_and_allows_add(self):
        r = self.run_command(reply(answer([add("첫 일")])))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["actions"], [out_add("첫 일")])
        self.create_mock.assert_called_once()
        content = self.create_mock.call_args.kwargs["messages"][0]["content"]
        self.assertIn("<tasks>\n\n</tasks>", content)

    def test_no_key_is_503_without_call(self):
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": ""}):
            r = self.run_command(reply("unused"))
        self.assertEqual(r.status_code, 503)
        self.assertEqual(r.json()["detail"], "AI 기능 꺼짐")
        self.create_mock.assert_not_called()

    def test_busy_is_503(self):
        for cls in (anthropic.RateLimitError, anthropic.OverloadedError):
            with self.subTest(cls=cls.__name__):
                r = self.run_command(error=api_error(cls))
                self.assertEqual(r.status_code, 503)
                self.assertEqual(r.json()["detail"], "AI 가 바쁩니다. 잠시 후 다시 시도하세요.")

    def test_auth_error_is_503(self):
        r = self.run_command(error=api_error(anthropic.AuthenticationError))
        self.assertEqual(r.status_code, 503)
        self.assertEqual(r.json()["detail"], "AI 기능 꺼짐")

    def test_connection_error_is_502(self):
        r = self.run_command(error=api_error(anthropic.APIConnectionError))
        self.assertEqual(r.status_code, 502)

    def test_text_length_rules_are_422_without_call(self):
        cases = {"empty": "", "blank": "   ", "too long": "가" * 201}
        for name, text in cases.items():
            with self.subTest(name):
                r = self.run_command(reply("unused"), text=text)
                self.assertEqual(r.status_code, 422, r.text)
                self.assertIn("명령", r.json()["detail"][0]["msg"])
                self.cls_mock.assert_not_called()
        with mock.patch("app.ai.anthropic.Anthropic") as cls:
            r = self.client.post("/api/tasks/command", json={})
        self.assertEqual(r.status_code, 422)
        cls.assert_not_called()

    def test_text_length_boundaries_pass(self):
        for text in ("가", "가" * 200):
            with self.subTest(n=len(text)):
                r = self.run_command(reply(answer([add()])), text=text)
                self.assertEqual(r.status_code, 200, r.text)

    def test_requires_login(self):
        with mock.patch("app.ai.anthropic.Anthropic") as cls:
            r = self.new_client().post("/api/tasks/command", json={"text": "x"})
        self.assertEqual(r.status_code, 401)
        cls.assert_not_called()

    def test_does_not_change_db(self):
        a = self.add_task(self.client, "x")
        before = self.rows()
        self.run_command(reply(answer([add("새"), due(a), done(a)])))
        self.assertEqual([tuple(r) for r in self.rows()], [tuple(r) for r in before])
