"""一覧スクリプトの安全なURLと表示の基本検証。"""

import importlib.util
from pathlib import Path
import unittest


SPEC = importlib.util.spec_from_file_location(
    "list_users", Path(__file__).with_name("list_users.py")
)
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class UserListTests(unittest.TestCase):
    def test_local_base_url_only(self):
        self.assertEqual(
            module.validate_base_url("http://localhost:8000/"), "http://localhost:8000"
        )
        for value in (
            "https://localhost:8000", "http://example.com:8000",
            "http://localhost:8000@other.example:8000", "http://localhost:8000/api",
            "http://localhost:8000?next=other", "http://localhost",
        ):
            with self.subTest(value=value), self.assertRaises(module.UserListError):
                module.validate_base_url(value)

    def test_table_uses_only_selected_fields_and_avoids_wide_character_shift(self):
        text = module.format_table([{
            "id": 5, "loginId": "takeuchi", "displayName": "竹内", "role": "member",
            "active": True, "departmentId": None, "history": [{"private": "unused"}],
        }])
        self.assertIn("5   takeuchi", text)
        self.assertRegex(text, r"竹内\s+member")
        self.assertNotIn("private", text)

    def test_demo_rejects_other_login(self):
        self.assertEqual(module.main(["--demo", "--login-id", "yuki"]), 1)


if __name__ == "__main__":
    unittest.main()
