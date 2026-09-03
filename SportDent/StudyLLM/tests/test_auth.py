import unittest

from app.auth import AuthManager


class AuthManagerTest(unittest.TestCase):
    def setUp(self):
        self.auth = AuthManager(username="tester", password="secret-pass", secret="fixed-secret", ttl_seconds=60)

    def test_credentials_require_exact_match(self):
        self.assertTrue(self.auth.authenticate("tester", "secret-pass"))
        self.assertFalse(self.auth.authenticate("tester", "wrong"))
        self.assertFalse(self.auth.authenticate("other", "secret-pass"))

    def test_signed_token_expires_and_rejects_tampering(self):
        token = self.auth.issue_token(now=100)
        self.assertTrue(self.auth.verify_token(token, now=159))
        self.assertFalse(self.auth.verify_token(token, now=160))
        self.assertFalse(self.auth.verify_token(token + "x", now=101))
        self.assertFalse(self.auth.verify_token(None, now=101))


if __name__ == "__main__":
    unittest.main()
