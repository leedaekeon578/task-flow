import os
from datetime import date
from types import SimpleNamespace
from unittest import mock

import anthropic

from app import ai
from test_tasks import TasksTestCase

TODAY = date(2026, 10, 27)
FAKE_KEY = "test-only-key"  # 실제 키가 아니다. 네트워크 호출은 모두 mock 이다.
GOOD = '{"priority": "HIGH", "due_date": "2026-10-30", "reason": "목요일까지라고 적혀 있습니다."}'


def reply(text: str, stop_reason: str = "end_turn", block_type: str = "text"):
    return SimpleNamespace(
        stop_reason=stop_reason, content=[SimpleNamespace(type=block_type, text=text)]
    )


def api_error(cls):
    # 응답 객체를 만들 필요 없이 예외 종류만 흉내 낸다.
    return cls.__new__(cls)


class SuggestTest(TasksTestCase):
    def setUp(self):
        super().setUp()
        for p in (
            mock.patch("app.rules.today", return_value=TODAY),
            mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": FAKE_KEY}),
        ):
            p.start()
            self.addCleanup(p.stop)
        self.client, _ = self.signup("a@test.com")

    def suggest(self, result=None, error=None, client=None, **body):
        body = {"title": "보고서 제출", "description": "목요일까지", **body}
        with mock.patch("app.ai.anthropic.Anthropic") as cls:
            create = cls.return_value.messages.create
            if error is not None:
                create.side_effect = error
            else:
                create.return_value = result
            r = (client or self.client).post("/api/tasks/suggest", json=body)
        self.create_mock, self.cls_mock = create, cls
        return r

    def task_rows(self):
        return self.sql("SELECT id, title, description, priority, due_date, updated_at FROM tasks")

    def test_success(self):
        r = self.suggest(reply(GOOD))
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(
            r.json(),
            {"priority": "HIGH", "due_date": "2026-10-30", "reason": "목요일까지라고 적혀 있습니다."},
        )

    def test_call_arguments(self):
        self.suggest(reply(GOOD), title="T", description="D")
        kw = self.create_mock.call_args.kwargs
        self.assertEqual(kw["model"], "claude-haiku-5-5")
        self.assertEqual(kw["thinking"], {"type": "disabled"})
        self.assertEqual(kw["max_tokens"], 512)
        self.assertEqual(kw["system"], ai.SYSTEM_PROMPT)
        self.assertEqual(
            kw["messages"],
            [
                {
                    "role": "user",
                    "content": "<today>2026-10-27</today>\n<title>T</title>\n<description>D</description>",
                }
            ],
        )
        init = self.cls_mock.call_args.kwargs
        self.assertEqual(init["api_key"], FAKE_KEY)
        self.assertEqual(init["timeout"], 20.0)

    def test_empty_description_is_empty_string(self):
        # description 을 안 보내면 빈 문자열로 넘긴다.
        with mock.patch("app.ai.anthropic.Anthropic") as cls:
            cls.return_value.messages.create.return_value = reply(GOOD)
            r = self.client.post("/api/tasks/suggest", json={"title": "x"})
        self.assertEqual(r.status_code, 200, r.text)
        content = cls.return_value.messages.create.call_args.kwargs["messages"][0]["content"]
        self.assertIn("<description></description>", content)

    def test_fenced_json(self):
        for text in (f"```json\n{GOOD}\n```", f"```\n{GOOD}\n```", f"  ```json\n{GOOD}```  "):
            with self.subTest(text=text):
                self.assertEqual(self.suggest(reply(text)).status_code, 200)

    def test_null_due_date_and_missing_priority_default(self):
        r = self.suggest(reply('{"due_date": null, "reason": "근거가 없어 기본값입니다."}'))
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["priority"], "NORMAL")
        self.assertIsNone(r.json()["due_date"])

    def test_invalid_answers_are_502(self):
        cases = {
            "bad priority": '{"priority": "URGENT", "due_date": null, "reason": "x"}',
            "lowercase priority": '{"priority": "high", "due_date": null, "reason": "x"}',
            "null priority": '{"priority": null, "due_date": null, "reason": "x"}',
            "bad date format": '{"priority": "LOW", "due_date": "2026/10/30", "reason": "x"}',
            "impossible date": '{"priority": "LOW", "due_date": "2026-02-30", "reason": "x"}',
            "missing reason": '{"priority": "LOW", "due_date": null}',
            "not json": "죄송합니다. 제안할 수 없습니다.",
            "json array": "[1, 2]",
            "empty": "",
            "unclosed fence": f"```json\n{GOOD}",
        }
        for name, text in cases.items():
            with self.subTest(name):
                r = self.suggest(reply(text))
                self.assertEqual(r.status_code, 502, r.text)
                self.assertEqual(r.json()["detail"], "제안 실패")

    def test_truncated_answer_is_502(self):
        r = self.suggest(reply(GOOD[:30], stop_reason="max_tokens"))
        self.assertEqual(r.status_code, 502)
        self.assertEqual(r.json()["detail"], "제안 실패")

    def test_non_text_block_is_502(self):
        r = self.suggest(reply(GOOD, block_type="thinking"))
        self.assertEqual(r.status_code, 502)

    def test_missing_key_is_503_and_no_call(self):
        env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
        for value in (None, "", "   "):
            with self.subTest(value=value):
                patched = dict(env) if value is None else {**env, "ANTHROPIC_API_KEY": value}
                with mock.patch.dict(os.environ, patched, clear=True):
                    r = self.suggest(reply(GOOD))
                self.assertEqual(r.status_code, 503)
                self.assertEqual(r.json()["detail"], "AI 기능 꺼짐")
                self.cls_mock.assert_not_called()

    def test_rate_limit_and_overloaded_are_503(self):
        for cls in (anthropic.RateLimitError, anthropic.OverloadedError):
            with self.subTest(cls=cls.__name__):
                r = self.suggest(error=api_error(cls))
                self.assertEqual(r.status_code, 503)
                self.assertEqual(r.json()["detail"], ai.BUSY)

    def test_bad_key_is_503_disabled(self):
        r = self.suggest(error=api_error(anthropic.AuthenticationError))
        self.assertEqual(r.status_code, 503)
        self.assertEqual(r.json()["detail"], "AI 기능 꺼짐")

    def test_other_api_errors_are_502(self):
        for cls in (anthropic.APIConnectionError, anthropic.APITimeoutError, anthropic.InternalServerError):
            with self.subTest(cls=cls.__name__):
                r = self.suggest(error=api_error(cls))
                self.assertEqual(r.status_code, 502)
                self.assertEqual(r.json()["detail"], "제안 실패")

    def test_requires_login(self):
        anon = self.new_client()
        r = self.suggest(reply(GOOD), client=anon)
        self.assertEqual(r.status_code, 401)
        self.cls_mock.assert_not_called()

    def test_request_validation(self):
        for body in ({"title": ""}, {"title": "   "}, {"title": "a" * 101}, {"description": "d"}):
            with self.subTest(body=body):
                r = self.client.post("/api/tasks/suggest", json=body)
                self.assertEqual(r.status_code, 422)

    def test_does_not_change_db(self):
        self.make_task(self.client, "기존", "내용")
        before = self.task_rows()
        users = self.sql("SELECT COUNT(*) FROM users")
        for result, error in ((reply(GOOD), None), (reply("not json"), None), (None, api_error(anthropic.RateLimitError))):
            self.suggest(result, error)
        self.assertEqual(self.task_rows(), before)
        self.assertEqual(self.sql("SELECT COUNT(*) FROM users"), users)

    def test_key_not_in_response(self):
        for result, error in ((reply(GOOD), None), (reply("not json"), None), (None, api_error(anthropic.AuthenticationError))):
            r = self.suggest(result, error)
            self.assertNotIn(FAKE_KEY, r.text)

    def test_other_task_routes_still_work(self):
        # /suggest 를 추가해도 /{task_id} 경로가 그대로 동작한다.
        t = self.make_task(self.client)
        self.assertEqual(self.client.patch(f"/api/tasks/{t['id']}/status", json={"status": "DONE"}).status_code, 200)
        self.assertEqual(self.client.delete(f"/api/tasks/{t['id']}").status_code, 204)
