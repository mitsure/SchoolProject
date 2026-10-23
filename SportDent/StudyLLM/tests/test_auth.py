import unittest

from app.auth import AuthManager, DEFAULT_SESSION_TTL_SECONDS


class AuthManagerTest(unittest.TestCase):
    def setUp(self):
        self.auth = AuthManager(username="tester", password="secret-pass", secret="fixed-secret", ttl_seconds=60)

    def test_credentials_require_exact_match(self):
        self.assertTrue(self.auth.authenticate("tester", "secret-pass"))
        self.assertFalse(self.auth.authenticate("tester", "wrong"))
        self.assertFalse(self.auth.authenticate("other", "secret-pass"))

    def test_unicode_credentials_require_exact_match(self):
        for username, password in (("研究者", "secret-pass"), ("tester", "試験用パスワード１２３"),
                                   ("研究者", "試験用パスワード🔑")):
            with self.subTest(username=username):
                auth = AuthManager(username=username, password=password, secret="fixed-secret")
                self.assertTrue(auth.authenticate(username, password))
                self.assertFalse(auth.authenticate(username + "別", password))
                self.assertFalse(auth.authenticate(username, password + "別"))
                self.assertTrue(auth.verify_token(auth.issue_token(now=100), now=101))

    def test_non_ascii_input_to_ascii_account_is_rejected_without_exception(self):
        for username, password in (("ｔｅｓｔｅｒ", "secret-pass"), ("tester", "パスワード"),
                                   ("tester", "secret-pass　"), ("研究者", "誤ったパスワード")):
            with self.subTest(username=username, password=password):
                self.assertFalse(self.auth.authenticate(username, password))

    def test_signed_token_expires_and_rejects_tampering(self):
        token = self.auth.issue_token(now=100)
        self.assertTrue(self.auth.verify_token(token, now=159))
        self.assertFalse(self.auth.verify_token(token, now=160))
        self.assertFalse(self.auth.verify_token(token + "x", now=101))
        self.assertFalse(self.auth.verify_token(None, now=101))

    def test_default_session_is_kept_for_thirty_days(self):
        auth = AuthManager(username="tester", password="secret-pass", secret="fixed-secret")
        token = auth.issue_token(now=100)
        self.assertTrue(auth.verify_token(token, now=100 + DEFAULT_SESSION_TTL_SECONDS - 1))
        self.assertFalse(auth.verify_token(token, now=100 + DEFAULT_SESSION_TTL_SECONDS))


if __name__ == "__main__":
    unittest.main()
