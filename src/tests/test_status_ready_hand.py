"""
Tests for status_ready_hand.py
"""
import json
import logging
from typing import cast

import pytest
from gspread import Spreadsheet, Worksheet
from pytest import LogCaptureFixture

from src.gsheets_integration.gsheet_handlers.status_ready_hand import (
    COL_DEVELOPER_MESSAGE,
    COL_STATUS_CODE,
    NOT_IMPLEMENTED_LABEL,
    _as_dict,  # pyright: ignore[reportPrivateUsage]
    _as_list,  # pyright: ignore[reportPrivateUsage]
    _as_str,  # pyright: ignore[reportPrivateUsage]
    _build_row_lookup,  # pyright: ignore[reportPrivateUsage]
    _cell_value,  # pyright: ignore[reportPrivateUsage]
    _developer_message_label,  # pyright: ignore[reportPrivateUsage]
    _find_header_value,  # pyright: ignore[reportPrivateUsage]
    _parse_json_body,  # pyright: ignore[reportPrivateUsage]
    update,
)
from src.schema import JSON

# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

class FakeWorksheet:
    """Minimal stand-in for gspread.Worksheet covering only the methods
    status_ready_hand.update relies on. Records every update_cell call so
    tests can assert on exactly what was written.
    """

    def __init__(self, rows: list[list[str]]) -> None:
        self._rows: list[list[str]] = rows
        self.update_calls: list[tuple[int, int, str]] = []

    def get_all_values(self) -> list[list[str]]:
        return self._rows

    def update_cell(self, row: int, col: int, value: str) -> dict[str, JSON]:
        self.update_calls.append((row, col, value))
        return {}


def _as_worksheet(fake: FakeWorksheet) -> Worksheet:
    """Casts a FakeWorksheet to Worksheet for call sites that are typed
    against the real gspread interface.
    """
    return cast(Worksheet, fake)


def _fake_spreadsheet() -> Spreadsheet:
    return cast(Spreadsheet, object())


def _bytes_to_stream(payload: dict[str, JSON]) -> dict[str, JSON]:
    """Builds a Newman-style response['stream'] object from a JSON payload."""
    encoded = json.dumps(payload).encode("utf-8")
    return {"type": "Buffer", "data": cast(JSON, list(encoded))}


def _make_report(
    collection_name: str,
    request_name: str,
    status_code: int,
    headers: list[JSON] | None = None,
    stream: dict[str, JSON] | None = None,
) -> dict[str, JSON]:
    response: dict[str, JSON] = {"code": status_code}
    if headers is not None:
        response["header"] = cast(JSON, headers)
    if stream is not None:
        response["stream"] = cast(JSON, stream)

    return {
        "collection": {"info": {"name": collection_name}},
        "run": {
            "executions": [
                {
                    "item": {"name": request_name},
                    "response": response,
                }
            ]
        },
    }


# ---------------------------------------------------------------------------
# _as_dict / _as_list / _as_str
# ---------------------------------------------------------------------------

def test_as_dict_returns_dict_for_valid_input() -> None:
    value: JSON = {"key": "value"}
    result = _as_dict(value, "context")
    assert result == {"key": "value"}


def test_as_dict_raises_type_error_for_non_dict() -> None:
    value: JSON = ["not", "a", "dict"]
    with pytest.raises(TypeError, match="expected 'context' to be a JSON object"):
        _ = _as_dict(value, "context")


def test_as_list_returns_list_for_valid_input() -> None:
    value: JSON = [1, 2, 3]
    result = _as_list(value, "context")
    assert result == [1, 2, 3]


def test_as_list_raises_type_error_for_non_list() -> None:
    value: JSON = {"not": "a list"}
    with pytest.raises(TypeError, match="expected 'context' to be a JSON array"):
        _ = _as_list(value, "context")


def test_as_str_returns_str_for_valid_input() -> None:
    value: JSON = "hello"
    result = _as_str(value, "context")
    assert result == "hello"


def test_as_str_raises_type_error_for_non_str() -> None:
    value: JSON = 123
    with pytest.raises(TypeError, match="expected 'context' to be a string"):
        _ = _as_str(value, "context")


# ---------------------------------------------------------------------------
# _find_header_value
# ---------------------------------------------------------------------------

def test_find_header_value_matches_case_insensitively() -> None:
    headers: JSON = [{"key": "Content-Type", "value": "application/json"}]
    assert _find_header_value(headers, "content-type") == "application/json"


def test_find_header_value_returns_none_when_absent() -> None:
    headers: JSON = [{"key": "Accept", "value": "*/*"}]
    assert _find_header_value(headers, "content-type") is None


def test_find_header_value_returns_none_for_non_list() -> None:
    headers: JSON = {"not": "a list"}
    assert _find_header_value(headers, "content-type") is None


def test_find_header_value_skips_malformed_entries() -> None:
    headers: JSON = ["not-a-dict", {"key": "Content-Type", "value": "application/json"}]
    assert _find_header_value(headers, "content-type") == "application/json"


# ---------------------------------------------------------------------------
# _parse_json_body
# ---------------------------------------------------------------------------

def test_parse_json_body_returns_none_without_content_type_header() -> None:
    response: dict[str, JSON] = {
        "header": [],
        "stream": _bytes_to_stream({"developerMessage": "x"}),
    }
    assert _parse_json_body(response) is None


def test_parse_json_body_returns_none_for_non_json_content_type() -> None:
    response: dict[str, JSON] = {
        "header": [{"key": "Content-Type", "value": "text/plain"}],
        "stream": _bytes_to_stream({"developerMessage": "x"}),
    }
    assert _parse_json_body(response) is None


def test_parse_json_body_parses_valid_json_stream() -> None:
    payload: dict[str, JSON] = {"developerMessage": "hello"}
    response: dict[str, JSON] = {
        "header": [{"key": "Content-Type", "value": "application/json; charset=utf-8"}],
        "stream": _bytes_to_stream(payload),
    }

    result = _parse_json_body(response)

    assert result == payload


def test_parse_json_body_returns_none_when_stream_missing() -> None:
    response: dict[str, JSON] = {
        "header": [{"key": "Content-Type", "value": "application/json"}],
    }
    assert _parse_json_body(response) is None


def test_parse_json_body_returns_none_when_stream_not_dict() -> None:
    response: dict[str, JSON] = {
        "header": [{"key": "Content-Type", "value": "application/json"}],
        "stream": "not-a-dict",
    }
    assert _parse_json_body(response) is None


def test_parse_json_body_returns_none_when_data_not_list() -> None:
    response: dict[str, JSON] = {
        "header": [{"key": "Content-Type", "value": "application/json"}],
        "stream": {"type": "Buffer", "data": "not-a-list"},
    }
    assert _parse_json_body(response) is None


def test_parse_json_body_returns_none_when_data_not_all_ints() -> None:
    response: dict[str, JSON] = {
        "header": [{"key": "Content-Type", "value": "application/json"}],
        "stream": {"type": "Buffer", "data": [1, 2, "not-an-int"]},
    }
    assert _parse_json_body(response) is None


def test_parse_json_body_returns_none_on_invalid_json(caplog: LogCaptureFixture) -> None:
    invalid_bytes = list(b"{not valid json")
    response: dict[str, JSON] = {
        "header": [{"key": "Content-Type", "value": "application/json"}],
        "stream": {"type": "Buffer", "data": cast(JSON, invalid_bytes)},
    }

    with caplog.at_level(logging.WARNING):
        result = _parse_json_body(response)

    assert result is None
    assert "Failed to parse response stream as JSON" in caplog.text


def test_parse_json_body_returns_none_on_invalid_utf8() -> None:
    invalid_bytes = [0xFF, 0xFE, 0xFD]
    response: dict[str, JSON] = {
        "header": [{"key": "Content-Type", "value": "application/json"}],
        "stream": {"type": "Buffer", "data": cast(JSON, invalid_bytes)},
    }

    assert _parse_json_body(response) is None


# ---------------------------------------------------------------------------
# _developer_message_label
# ---------------------------------------------------------------------------

def test_developer_message_label_matches_exact_message() -> None:
    body: JSON = {"developerMessage": "The operation has not been implemented"}
    assert _developer_message_label(body) == NOT_IMPLEMENTED_LABEL


def test_developer_message_label_returns_none_for_different_message() -> None:
    body: JSON = {"developerMessage": "Some other message"}
    assert _developer_message_label(body) is None


def test_developer_message_label_returns_none_when_body_not_dict() -> None:
    body: JSON = ["not", "a", "dict"]
    assert _developer_message_label(body) is None


def test_developer_message_label_returns_none_when_body_is_none() -> None:
    assert _developer_message_label(None) is None


def test_developer_message_label_returns_none_when_key_missing() -> None:
    body: JSON = {"someOtherKey": "value"}
    assert _developer_message_label(body) is None


# ---------------------------------------------------------------------------
# _build_row_lookup / _cell_value
# ---------------------------------------------------------------------------

def test_build_row_lookup_maps_col_a_and_d_to_row_number() -> None:
    rows: list[list[str]] = [
        ["Collection", "B", "C", "Request"],  # header
        ["My Collection", "x", "y", "Get Users", "z"],
        ["My Collection", "x", "y", "Post Users", "z"],
    ]

    lookup = _build_row_lookup(rows)

    assert lookup[("My Collection", "Get Users")] == 2
    assert lookup[("My Collection", "Post Users")] == 3


def test_build_row_lookup_handles_short_rows() -> None:
    rows: list[list[str]] = [
        ["Collection", "B", "C", "Request"],
        ["My Collection"],  # missing col D and beyond
    ]

    lookup = _build_row_lookup(rows)

    assert lookup[("My Collection", "")] == 2


def test_cell_value_returns_value_when_present() -> None:
    row = ["a", "b", "c", "d", "e", "f", "g"]
    assert _cell_value(row, 7) == "g"


def test_cell_value_returns_empty_string_when_row_too_short() -> None:
    row = ["a", "b"]
    assert _cell_value(row, 7) == ""


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------

def test_update_writes_status_code_when_row_matches() -> None:
    report = _make_report("My Collection", "Get Users", 200)
    rows: list[list[str]] = [
        ["Collection", "B", "C", "Request", "E", "F", "G", "H", "I"],
        ["My Collection", "", "", "Get Users", "", "", "", "", ""],
    ]
    fake_worksheet = FakeWorksheet(rows)

    update(cast(JSON, report), _fake_spreadsheet(), _as_worksheet(fake_worksheet))

    assert (2, COL_STATUS_CODE, "200") in fake_worksheet.update_calls


def test_update_skips_status_code_when_already_matching() -> None:
    report = _make_report("My Collection", "Get Users", 200)
    rows: list[list[str]] = [
        ["Collection", "B", "C", "Request", "E", "F", "G", "H", "I"],
        ["My Collection", "", "", "Get Users", "", "", "200", "", ""],
    ]
    fake_worksheet = FakeWorksheet(rows)

    update(cast(JSON, report), _fake_spreadsheet(), _as_worksheet(fake_worksheet))

    assert fake_worksheet.update_calls == []


def test_update_skips_execution_with_no_matching_row(caplog: LogCaptureFixture) -> None:
    report = _make_report("My Collection", "Unknown Request", 200)
    rows: list[list[str]] = [
        ["Collection", "B", "C", "Request", "E", "F", "G", "H", "I"],
        ["My Collection", "", "", "Get Users", "", "", "", "", ""],
    ]
    fake_worksheet = FakeWorksheet(rows)

    with caplog.at_level(logging.WARNING):
        update(cast(JSON, report), _fake_spreadsheet(), _as_worksheet(fake_worksheet))

    assert fake_worksheet.update_calls == []
    assert "No matching row" in caplog.text


def test_update_writes_not_implemented_label_when_developer_message_matches() -> None:
    headers: list[JSON] = [{"key": "Content-Type", "value": "application/json"}]
    stream = _bytes_to_stream({"developerMessage": "The operation has not been implemented"})
    report = _make_report("My Collection", "Get Users", 501, headers=headers, stream=stream)

    rows: list[list[str]] = [
        ["Collection", "B", "C", "Request", "E", "F", "G", "H", "I"],
        ["My Collection", "", "", "Get Users", "", "", "", "", ""],
    ]
    fake_worksheet = FakeWorksheet(rows)

    update(cast(JSON, report), _fake_spreadsheet(), _as_worksheet(fake_worksheet))

    assert (2, COL_STATUS_CODE, "501") in fake_worksheet.update_calls
    assert (2, COL_DEVELOPER_MESSAGE, NOT_IMPLEMENTED_LABEL) in fake_worksheet.update_calls


def test_update_does_not_write_label_when_developer_message_differs() -> None:
    headers: list[JSON] = [{"key": "Content-Type", "value": "application/json"}]
    stream = _bytes_to_stream({"developerMessage": "Something else entirely"})
    report = _make_report("My Collection", "Get Users", 500, headers=headers, stream=stream)

    rows: list[list[str]] = [
        ["Collection", "B", "C", "Request", "E", "F", "G", "H", "I"],
        ["My Collection", "", "", "Get Users", "", "", "", "", ""],
    ]
    fake_worksheet = FakeWorksheet(rows)

    update(cast(JSON, report), _fake_spreadsheet(), _as_worksheet(fake_worksheet))

    assert all(call[1] != COL_DEVELOPER_MESSAGE for call in fake_worksheet.update_calls)


def test_update_skips_label_write_when_already_matching() -> None:
    headers: list[JSON] = [{"key": "Content-Type", "value": "application/json"}]
    stream = _bytes_to_stream({"developerMessage": "The operation has not been implemented"})
    report = _make_report("My Collection", "Get Users", 501, headers=headers, stream=stream)

    rows: list[list[str]] = [
        ["Collection", "B", "C", "Request", "E", "F", "G", "H", "I"],
        ["My Collection", "", "", "Get Users", "", "", "501", "", NOT_IMPLEMENTED_LABEL],
    ]
    fake_worksheet = FakeWorksheet(rows)

    update(cast(JSON, report), _fake_spreadsheet(), _as_worksheet(fake_worksheet))

    assert fake_worksheet.update_calls == []


def test_update_raises_type_error_on_malformed_report() -> None:
    malformed_report: JSON = {"collection": {"info": {}}}  # missing 'name'

    with pytest.raises(TypeError, match="collection.info.name"):
        update(malformed_report, _fake_spreadsheet(), _as_worksheet(FakeWorksheet([[]])))


def test_update_raises_type_error_on_malformed_execution() -> None:
    report: JSON = {
        "collection": {"info": {"name": "My Collection"}},
        "run": {"executions": ["not-a-dict"]},
    }

    with pytest.raises(TypeError, match=r"run\.executions\[0\]"):
        update(report, _fake_spreadsheet(), _as_worksheet(FakeWorksheet([[]])))


def test_update_logs_summary_counts(caplog: LogCaptureFixture) -> None:
    report = _make_report("My Collection", "Get Users", 200)
    rows: list[list[str]] = [
        ["Collection", "B", "C", "Request", "E", "F", "G", "H", "I"],
        ["My Collection", "", "", "Get Users", "", "", "", "", ""],
    ]
    fake_worksheet = FakeWorksheet(rows)

    with caplog.at_level(logging.INFO):
        update(cast(JSON, report), _fake_spreadsheet(), _as_worksheet(fake_worksheet))

    assert "Syncing 1 execution(s)" in caplog.text
    assert "Sheet sync complete" in caplog.text
