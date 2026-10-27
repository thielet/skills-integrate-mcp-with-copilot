import unittest
from unittest.mock import patch

from fastapi import HTTPException

import auth


class TeacherAuthTests(unittest.TestCase):
    def setUp(self):
        auth.sessions.clear()
        self.record = auth.make_password_record("teacher", "correct horse battery")
        self.teachers = {"teacher": self.record}

    def tearDown(self):
        auth.sessions.clear()

    def test_password_authentication(self):
        with patch.object(auth, "load_teachers", return_value=self.teachers):
            self.assertTrue(auth.authenticate_teacher("teacher", "correct horse battery"))
            self.assertFalse(auth.authenticate_teacher("teacher", "wrong password"))
            self.assertFalse(auth.authenticate_teacher("unknown", "correct horse battery"))

    def test_session_requires_existing_teacher_and_expires(self):
        with patch.object(auth, "load_teachers", return_value=self.teachers):
            session_token = auth.create_session("teacher")
            self.assertEqual(auth.get_optional_teacher(session_token), "teacher")

            with patch.object(auth.time, "time", return_value=float("inf")):
                self.assertIsNone(auth.get_optional_teacher(session_token))

    def test_mutation_dependency_rejects_anonymous_user(self):
        with self.assertRaises(HTTPException) as error:
            auth.require_teacher(None)
        self.assertEqual(error.exception.status_code, 401)


if __name__ == "__main__":
    unittest.main()