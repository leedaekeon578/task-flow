import json
import os
from datetime import date
from types import SimpleNamespace
from unittest import mock

import anthropic

from app import ai
from test_tasks import TasksTestCase

TODAY = date(2026, 10, 28)
FAKE_KEY = "test-only-key"  # 실제 키가 아니다. 네트워크 호출은 모두 mock 이다.


def item(title="견적 받기", priority="HIGH", due_date="2026-10-30"):
    return {"title": title, "priority": priority, "due_date": due_date}


def answer(*items):
    return json.dumps({"tasks": list(items)}, ensure_ascii=False)


THREE = [item("a"), item("b", "NORMAL", None), item("c", "LOW", "2026-11-01")]
GOOD = answer(*THREE)


def reply(text: str, stop_reason: str = "end_turn", block_type: str = "text"):
    return SimpleNamespace(
        stop_reason=stop_reason, content=[SimpleNamespace(type=block_type, text=text)]
    )


def api_error(cls):
    return cls.__new__(cls)


class GenerateTest(TasksTestCase):
    def setUp(self):
        super().setUp()
        for p in (
            mock.patch("app.rules.today", return_value=TODAY),
            mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": FAKE_KEY}),
        ):
            p.start()
            self.addCleanup(p.stop)
        self.client, _ = self.signup("a@test.com")

    def generate(self, result=None, error=None, client=None, **body):
        body = {"topic": "이사 준비", **body}
        with mock.patch("app.ai.anthropic.Anthropic") as cls:
            create = cls.return_value.messages.create
            if error is not None:
                create.side_effect = error
            else:
                create.return_value = result
            r = (client or self.client).post("/api/tasks/generate", json=body)
        self.create_mock, self.cls_mock = create, cls
        return r

    def task_rows(self):
        return self.sql("SELECT id, title, description, priority, due_date, updated_at FROM tasks")

    def test_success(self):
        r = self.generate(reply(GOOD))
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json(), {"tasks": THREE})

    def test_three_to_five_allowed(self):
        for n in (3, 4, 5):
            with self.subTest(n=n):
                r = self.generate(reply(answer(*[item(f"t{i}") for i in range(n)])))
                self.assertEqual(r.status_code, 200, r.text)
                self.assertEqual(len(r.json()["tasks"]), n)

    def test_call_arguments(self):
        self.generate(reply(GOOD), topic="T")
        kw = self.create_mock.call_args.kwargs
        self.assertEqual(kw["model"], "claude-haiku-5-5")
        self.assertEqual(kw["thinking"], {"type": "disabled"})
        self.assertEqual(kw["max_tokens"], 1024)
        self.assertEqual(kw["system"], ai.GENERATE_SYSTEM_PROMPT)
        self.assertEqual(
            kw["messages"],
            [{"role": "user", "content": "<today>2026-10-28</today>\n<topic>T</topic>"}],
        )
        init = self.cls_mock.call_args.kwargs
        self.assertEqual(init["api_key"], FAKE_KEY)
        self.assertEqual(init["timeout"], 20.0)
        self.assertEqual(init["max_retries"], 0)

    def test_fenced_json(self):
        for text in (f"```json\n{GOOD}\n```", f"```\n{GOOD}\n```"):
            with self.subTest(text=text):
                self.assertEqual(self.generate(reply(text)).status_code, 200)

    def test_invalid_answers_are_502(self):
        cases = {
            "two items": answer(item(), item()),
            "six items": answer(*[item(f"t{i}") for i in range(6)]),
            "no items": answer(),
            "missing priority": answer(item(), item(), {"title": "x", "due_date": None}),
            "missing due_date": answer(item(), item(), {"title": "x", "priority": "LOW"}),
            "missing title": answer(item(), item(), {"priority": "LOW", "due_date": None}),
            "blank title": answer(item(), item(), item("  ")),
            "bad priority": answer(item(), item(), item(priority="URGENT")),
            "lowercase priority": answer(item(), item(), item(priority="high")),
            "null priority": answer(item(), item(), item(priority=None)),
            "bad date format": answer(item(), item(), item(due_date="2026/10/30")),
            "impossible date": answer(item(), item(), item(due_date="2026-02-30")),
            "tasks not list": '{"tasks": "x"}',
            "no tasks key": '{"items": []}',
            "not json": "죄송합니다.",
            "json array": "[1, 2]",
            "empty": "",
            "unclosed fence": f"```json\n{GOOD}",
        }
        for name, text in cases.items():
            with self.subTest(name):
                r = self.generate(reply(text))
                self.assertEqual(r.status_code, 502, r.text)
                self.assertEqual(r.json()["detail"], "제안 실패")

    def test_truncated_answer_is_502(self):
        r = self.generate(reply(GOOD[:30], stop_reason="max_tokens"))
        self.assertEqual(r.status_code, 502)
        self.assertEqual(r.json()["detail"], "제안 실패")

    def test_non_text_block_is_502(self):
        self.assertEqual(self.generate(reply(GOOD, block_type="thinking")).status_code, 502)

    def test_missing_key_is_503_and_no_call(self):
        env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
        for value in (None, "", "   "):
            with self.subTest(value=value):
                patched = dict(env) if value is None else {**env, "ANTHROPIC_API_KEY": value}
                with mock.patch.dict(os.environ, patched, clear=True):
                    r = self.generate(reply(GOOD))
                self.assertEqual(r.status_code, 503)
                self.assertEqual(r.json()["detail"], "AI 기능 꺼짐")
                self.cls_mock.assert_not_called()

    def test_rate_limit_and_overloaded_are_503(self):
        for cls in (anthropic.RateLimitError, anthropic.OverloadedError):
            with self.subTest(cls=cls.__name__):
                r = self.generate(error=api_error(cls))
                self.assertEqual(r.status_code, 503)
                self.assertEqual(r.json()["detail"], ai.BUSY)

    def test_bad_key_is_503_disabled(self):
        r = self.generate(error=api_error(anthropic.AuthenticationError))
        self.assertEqual(r.status_code, 503)
        self.assertEqual(r.json()["detail"], "AI 기능 꺼짐")

    def test_other_api_errors_are_502(self):
        for cls in (anthropic.APIConnectionError, anthropic.APITimeoutError, anthropic.InternalServerError):
            with self.subTest(cls=cls.__name__):
                r = self.generate(error=api_error(cls))
                self.assertEqual(r.status_code, 502)
                self.assertEqual(r.json()["detail"], "제안 실패")

    def test_requires_login(self):
        r = self.generate(reply(GOOD), client=self.new_client())
        self.assertEqual(r.status_code, 401)
        self.cls_mock.assert_not_called()

    def test_request_validation(self):
        for body in ({"topic": ""}, {"topic": "   "}, {"topic": "a" * 101}, {}):
            with self.subTest(body=body):
                r = self.client.post("/api/tasks/generate", json=body)
                self.assertEqual(r.status_code, 422)

    def test_topic_100_chars_ok(self):
        self.assertEqual(self.generate(reply(GOOD), topic="a" * 100).status_code, 200)

    def test_does_not_change_db(self):
        self.make_task(self.client, "기존", "내용")
        before = self.task_rows()
        users = self.sql("SELECT COUNT(*) FROM users")
        for result, error in ((reply(GOOD), None), (reply("not json"), None), (None, api_error(anthropic.RateLimitError))):
            self.generate(result, error)
        self.assertEqual(self.task_rows(), before)
        self.assertEqual(self.sql("SELECT COUNT(*) FROM users"), users)

    def test_key_not_in_response(self):
        for result, error in ((reply(GOOD), None), (reply("not json"), None), (None, api_error(anthropic.AuthenticationError))):
            self.assertNotIn(FAKE_KEY, self.generate(result, error).text)

    def test_other_task_routes_still_work(self):
        t = self.make_task(self.client)
        self.assertEqual(self.client.patch(f"/api/tasks/{t['id']}/status", json={"status": "DONE"}).status_code, 200)
        self.assertEqual(self.client.delete(f"/api/tasks/{t['id']}").status_code, 204)
