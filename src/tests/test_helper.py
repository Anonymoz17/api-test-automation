import re

from src.utils.helper import get_datetime, sanitize


class TestSanitize:
    def test_strips_surrounding_whitespace(self) -> None:
        assert sanitize(text="  hello  ") == "hello"

    def test_removes_special_characters(self) -> None:
        assert sanitize(text="Order #123 (v2)!") == "Order 123 v2"

    def test_keeps_alphanumeric_and_spaces(self) -> None:
        assert sanitize(text="Agent v1 2024") == "Agent v1 2024"


class TestGetDatetime:
    def test_matches_expected_format(self) -> None:
        assert re.fullmatch(r"\d{8}_\d{6}", get_datetime())
