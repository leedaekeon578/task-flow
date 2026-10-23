import unittest

from app.config import ConfigError, load_session_secret
from app.security import (
    hash_password,
    hash_session_token,
    new_session_token,
    verify_password,
)


class SessionSecretTest(unittest.TestCase):
    def test_missing_or_blank_is_rejected(self):
        for env in ({}, {"SESSION_SECRET": ""}, {"SESSION_SECRET": "   "}):
            with self.subTest(env=env):
                with self.assertRaises(ConfigError):
                    load_session_secret(env)

    def test_value_is_returned(self):
        self.assertEqual(load_session_secret({"SESSION_SECRET": "abc"}), "abc")


class PasswordTest(unittest.TestCase):
    def test_hash_is_argon2_and_not_plaintext(self):
        h = hash_password("correct horse")
        self.assertTrue(h.startswith("$argon2"))
        self.assertNotIn("correct horse", h)
        self.assertNotEqual(h, hash_password("correct horse"))  # 솔트

    def test_verify(self):
        h = hash_password("correct horse")
        self.assertTrue(verify_password(h, "correct horse"))
        self.assertFalse(verify_password(h, "wrong"))

    def test_no_hash_never_verifies(self):
        # 이전용 계정(해시 없음)은 로그인할 수 없다.
        self.assertFalse(verify_password(None, "anything"))
        self.assertFalse(verify_password(None, ""))

    def test_garbage_hash_does_not_verify(self):
        self.assertFalse(verify_password("not-a-hash", "x"))


class SessionTokenTest(unittest.TestCase):
    def test_tokens_are_random(self):
        self.assertNotEqual(new_session_token(), new_session_token())

    def test_hash_is_stable_keyed_and_hides_token(self):
        t = new_session_token()
        h = hash_session_token(t, "s1")
        self.assertEqual(h, hash_session_token(t, "s1"))
        self.assertNotEqual(h, hash_session_token(t, "s2"))
        self.assertNotIn(t, h)
