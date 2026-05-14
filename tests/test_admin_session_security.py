import unittest
import sys
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) in sys.path:
    sys.path.remove(str(APP_ROOT))
sys.path.insert(0, str(APP_ROOT))
from server import AdminSessionStore


class AdminSessionSecurityTest(unittest.TestCase):
    def test_admin_password_is_stored_as_pbkdf2_hash_and_verified(self):
        sessions = AdminSessionStore("admin", "correct-horse-battery-staple", "session-secret")

        self.assertTrue(sessions.password_hash.startswith("pbkdf2_sha256$"))
        self.assertTrue(sessions.verify_credentials("admin", "correct-horse-battery-staple"))
        self.assertFalse(sessions.verify_credentials("admin", "wrong-password"))
        self.assertFalse(sessions.verify_credentials("other", "correct-horse-battery-staple"))

    def test_destroy_session_revokes_token_until_expiry(self):
        sessions = AdminSessionStore("admin", "correct-horse-battery-staple", "session-secret")
        token = sessions.create_session()

        self.assertIsNotNone(sessions.get_session(token))
        sessions.destroy_session(token)
        self.assertIsNone(sessions.get_session(token))


if __name__ == "__main__":
    unittest.main()
