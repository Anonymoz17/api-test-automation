"""
Tests for src.postman_api.export_collections

Assumes this file lives at tests/postman_api/test_export_collections.py
(or anywhere on a path where `src` is importable as a top-level package).

Typing notes (for basedpyright strict mode):
- Fake HTTP responses use a small `FakeResponse` class instead of MagicMock,
  so `.json()` has a real `-> JSON` return type instead of `Any`.
- Collection fixtures are built as `JSON` and only `cast` to `CollectionResponse`
  where a typed collection argument is actually required — mirroring the
  `cast(CollectionResponse, cast(object, body))` pattern in the production
  code itself, since `CollectionResponse` (per src.schema) also requires a
  "collections" key that single-collection API responses don't actually have.
- `monkeypatch.setattr(ec, "sanitize", ...)` / `"get_datetime"` intentionally
  patch the names as imported into `export_collections`'s own namespace
  (that's where `generate_filename` looks them up) rather than their
  defining module. basedpyright's reportPrivateLocalImportUsage flags this
  as reaching into another module's "private" re-export, which is correct
  in general but is exactly the standard monkeypatch pattern here, so those
  two lines carry a narrow, explicit pyright: ignore.
"""

import json
from collections.abc import Callable
from pathlib import Path
from typing import cast
from unittest.mock import MagicMock

import pytest
import requests

from src.env import POSTMAN_API_HEADERS
from src.postman_api import export_collections as ec
from src.schema import JSON, CollectionResponse

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

class FakeResponse:
    """Minimal stand-in for requests.Response covering what fetch_collection uses."""

    def __init__(
        self,
        *,
        json_data: JSON = None,
        ok: bool = True,
        status_code: int = 200,
        json_exception: Exception | None = None,
    ) -> None:
        self._json_data: JSON = json_data
        self._json_exception: Exception | None = json_exception
        self.ok: bool = ok
        self.status_code: int = status_code

    def json(self) -> JSON:
        if self._json_exception is not None:
            raise self._json_exception
        return self._json_data


def _stub_get(
    *,
    response: FakeResponse | None = None,
    exception: Exception | None = None,
) -> Callable[..., FakeResponse]:
    """Builds a stand-in for requests.get matching fetch_collection's (url=, headers=, timeout=) call."""

    def _get(*, url: str, headers: object, timeout: int) -> FakeResponse:
        _ = (url, headers, timeout)
        if exception is not None:
            raise exception
        assert response is not None
        return response

    return _get


def valid_collection_payload(name: str = "My Collection", uid: str = "abc-123") -> JSON:
    """Raw JSON shape of a successful single-collection API response."""
    return {
        "collection": {
            "info": {"name": name, "uid": uid},
            "name": name,
            "uid": uid,
        }
    }


def valid_collection(name: str = "My Collection", uid: str = "abc-123") -> CollectionResponse:
    """Typed CollectionResponse view of the same payload, for use as a function argument."""
    return cast(CollectionResponse, cast(object, valid_collection_payload(name=name, uid=uid)))


def malformed_collection(payload: JSON) -> CollectionResponse:
    """Builds a CollectionResponse-typed value from an arbitrary/malformed JSON shape,
    for exercising generate_filename's defensive handling of bad data."""
    return cast(CollectionResponse, cast(object, payload))


# ---------------------------------------------------------------------------
# fetch_collection
# ---------------------------------------------------------------------------

class TestFetchCollection:
    def test_returns_collection_on_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        payload = valid_collection_payload()
        response = FakeResponse(json_data=payload, ok=True, status_code=200)
        get_mock = MagicMock(side_effect=_stub_get(response=response))
        monkeypatch.setattr(requests, "get", get_mock)

        result = ec.fetch_collection(collection_uid="abc-123")

        assert result == payload
        get_mock.assert_called_once_with(
            url=ec.TARGET_URL + "/abc-123",
            headers=POSTMAN_API_HEADERS,
            timeout=ec.REQUEST_TIMEOUT_SECONDS,
        )

    def test_raises_when_response_not_ok(self, monkeypatch: pytest.MonkeyPatch) -> None:
        payload: JSON = {"error": {"name": "instanceNotFoundError", "message": "not found"}}
        response = FakeResponse(json_data=payload, ok=False, status_code=404)
        monkeypatch.setattr(requests, "get", MagicMock(side_effect=_stub_get(response=response)))

        with pytest.raises(RuntimeError, match="Failed to fetch collection 'missing-uid'"):
            _ = ec.fetch_collection(collection_uid="missing-uid")

    def test_raises_when_collection_key_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        payload: JSON = {"unexpected": "shape"}
        response = FakeResponse(json_data=payload, ok=True, status_code=200)
        monkeypatch.setattr(requests, "get", MagicMock(side_effect=_stub_get(response=response)))

        with pytest.raises(RuntimeError, match="Failed to fetch collection 'abc-123'"):
            _ = ec.fetch_collection(collection_uid="abc-123")

    def test_raises_when_body_is_not_a_dict(self, monkeypatch: pytest.MonkeyPatch) -> None:
        payload: JSON = ["not", "a", "dict"]
        response = FakeResponse(json_data=payload, ok=True, status_code=200)
        monkeypatch.setattr(requests, "get", MagicMock(side_effect=_stub_get(response=response)))

        with pytest.raises(RuntimeError, match="Failed to fetch collection 'abc-123'"):
            _ = ec.fetch_collection(collection_uid="abc-123")

    def test_error_message_includes_error_detail_from_body(self, monkeypatch: pytest.MonkeyPatch) -> None:
        payload: JSON = {"error": {"name": "unauthorized", "message": "bad api key"}}
        response = FakeResponse(json_data=payload, ok=False, status_code=401)
        monkeypatch.setattr(requests, "get", MagicMock(side_effect=_stub_get(response=response)))

        with pytest.raises(RuntimeError) as exc_info:
            _ = ec.fetch_collection(collection_uid="abc-123")

        assert "bad api key" in str(exc_info.value)
        assert "401" in str(exc_info.value)

    def test_error_message_uses_raw_body_when_not_a_dict(self, monkeypatch: pytest.MonkeyPatch) -> None:
        response = FakeResponse(json_data="plain text error", ok=False, status_code=500)
        monkeypatch.setattr(requests, "get", MagicMock(side_effect=_stub_get(response=response)))

        with pytest.raises(RuntimeError, match="plain text error"):
            _ = ec.fetch_collection(collection_uid="abc-123")

    def test_raises_runtime_error_on_network_failure(self, monkeypatch: pytest.MonkeyPatch) -> None:
        exc = requests.exceptions.ConnectionError("connection refused")
        monkeypatch.setattr(requests, "get", MagicMock(side_effect=_stub_get(exception=exc)))

        with pytest.raises(RuntimeError, match="network error"):
            _ = ec.fetch_collection(collection_uid="abc-123")

    def test_raises_runtime_error_on_timeout(self, monkeypatch: pytest.MonkeyPatch) -> None:
        exc = requests.exceptions.Timeout("timed out")
        monkeypatch.setattr(requests, "get", MagicMock(side_effect=_stub_get(exception=exc)))

        with pytest.raises(RuntimeError, match="network error"):
            _ = ec.fetch_collection(collection_uid="abc-123")

    def test_raises_runtime_error_on_invalid_json(self, monkeypatch: pytest.MonkeyPatch) -> None:
        response = FakeResponse(ok=True, status_code=200, json_exception=ValueError("bad json"))
        monkeypatch.setattr(requests, "get", MagicMock(side_effect=_stub_get(response=response)))

        with pytest.raises(RuntimeError, match="not valid JSON"):
            _ = ec.fetch_collection(collection_uid="abc-123")


# ---------------------------------------------------------------------------
# resolve_and_fetch_collections
# ---------------------------------------------------------------------------

class TestResolveAndFetchCollections:
    def test_single_uid_string(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def _fetch(*, collection_uid: str) -> CollectionResponse:
            _ = collection_uid
            return valid_collection()

        fetch_mock = MagicMock(side_effect=_fetch)
        monkeypatch.setattr(ec, "fetch_collection", fetch_mock)

        result = ec.resolve_and_fetch_collections(collection_uids="uid-1")

        fetch_mock.assert_called_once_with(collection_uid="uid-1")
        assert result == [valid_collection()]

    def test_list_of_uids(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def _fetch(*, collection_uid: str) -> CollectionResponse:
            return valid_collection(uid=collection_uid)

        fetch_mock = MagicMock(side_effect=_fetch)
        monkeypatch.setattr(ec, "fetch_collection", fetch_mock)

        result = ec.resolve_and_fetch_collections(collection_uids=["uid-1", "uid-2"])

        assert fetch_mock.call_count == 2
        assert [c["collection"]["uid"] for c in result] == ["uid-1", "uid-2"]

    def test_empty_string_input_is_passed_through_as_a_single_uid(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def _fetch(*, collection_uid: str) -> CollectionResponse:
            return valid_collection(uid=collection_uid)

        fetch_mock = MagicMock(side_effect=_fetch)
        monkeypatch.setattr(ec, "fetch_collection", fetch_mock)

        # An empty string is treated as a single uid (not "no uids"), so it's
        # passed straight to fetch_collection rather than short-circuited.
        _ = ec.resolve_and_fetch_collections(collection_uids="")
        fetch_mock.assert_called_once_with(collection_uid="")

    def test_empty_list_raises_value_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fetch_mock = MagicMock()
        monkeypatch.setattr(ec, "fetch_collection", fetch_mock)

        with pytest.raises(ValueError, match="No collection UIDs provided"):
            _ = ec.resolve_and_fetch_collections(collection_uids=[])

        fetch_mock.assert_not_called()

    def test_propagates_fetch_failures(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def _raise_boom(*, collection_uid: str) -> CollectionResponse:
            raise RuntimeError(f"boom ({collection_uid})")

        fetch_mock = MagicMock(side_effect=_raise_boom)
        monkeypatch.setattr(ec, "fetch_collection", fetch_mock)

        with pytest.raises(RuntimeError, match="boom"):
            _ = ec.resolve_and_fetch_collections(collection_uids=["uid-1"])


# ---------------------------------------------------------------------------
# generate_filename
# ---------------------------------------------------------------------------

class TestGenerateFilename:
    def test_uses_sanitized_name_when_present(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def _sanitize(*, text: str) -> str:
            return f"sanitized-{text}"

        def _get_datetime() -> str:
            return "20260101-000000"

        monkeypatch.setattr(ec, "sanitize", _sanitize)
        monkeypatch.setattr(ec, "get_datetime", _get_datetime)

        collection = valid_collection(name="My Collection", uid="uid-1")
        filename = ec.generate_filename(collection=collection)

        assert filename == "sanitized-My Collection_20260101-000000"

    def test_falls_back_to_uid_when_name_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        sanitize_mock = MagicMock()

        def _get_datetime() -> str:
            return "20260101-000000"

        monkeypatch.setattr(ec, "sanitize", sanitize_mock) 
        monkeypatch.setattr(ec, "get_datetime", _get_datetime)

        collection = valid_collection(name="", uid="uid-only")
        filename = ec.generate_filename(collection=collection)

        sanitize_mock.assert_not_called()
        assert filename == "uid-only_20260101-000000"

    def test_appends_datetime_suffix(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def _sanitize(*, text: str) -> str:
            return text

        def _get_datetime() -> str:
            return "TIMESTAMP"

        monkeypatch.setattr(ec, "sanitize", _sanitize) 
        monkeypatch.setattr(ec, "get_datetime", _get_datetime) 

        collection = valid_collection(name="Foo", uid="uid-1")
        filename = ec.generate_filename(collection=collection)

        assert filename.endswith("_TIMESTAMP")

    def test_raises_when_name_and_uid_both_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def _get_datetime() -> str:
            return "TIMESTAMP"

        monkeypatch.setattr(ec, "get_datetime", _get_datetime) 
        collection = malformed_collection(
            {"collection": {"info": {"name": "", "uid": ""}, "name": "", "uid": ""}}
        )

        with pytest.raises(ValueError, match="neither a usable name nor a uid"):
            _ = ec.generate_filename(collection=collection)

    def test_raises_when_info_missing_entirely(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def _get_datetime() -> str:
            return "TIMESTAMP"

        monkeypatch.setattr(ec, "get_datetime", _get_datetime)  
        collection = malformed_collection({"collection": {}})

        with pytest.raises(ValueError, match="neither a usable name nor a uid"):
            _ = ec.generate_filename(collection=collection)


# ---------------------------------------------------------------------------
# write_file
# ---------------------------------------------------------------------------

class TestWriteFile:
    def test_writes_json_to_path(self, tmp_path: Path) -> None:
        data = valid_collection()
        output_path = tmp_path / "collection.json"

        ec.write_file(data=data, output_path=output_path)

        assert output_path.exists()
        written: JSON = json.loads(output_path.read_text(encoding="utf-8"))
        assert written == data

    def test_writes_with_indentation(self, tmp_path: Path) -> None:
        data = valid_collection()
        output_path = tmp_path / "out.json"

        ec.write_file(data=data, output_path=output_path)

        content = output_path.read_text(encoding="utf-8")
        assert "\n" in content  # json.dump(..., indent=4) produces multi-line output

    def test_creates_missing_parent_directories(self, tmp_path: Path) -> None:
        data = valid_collection()
        output_path = tmp_path / "nested" / "dirs" / "collection.json"

        ec.write_file(data=data, output_path=output_path)

        assert output_path.exists()
        written: JSON = json.loads(output_path.read_text(encoding="utf-8"))
        assert written == data

    def test_raises_runtime_error_when_parent_cannot_be_created(self, tmp_path: Path) -> None:
        # Create a *file* where write_file expects to create a *directory*,
        # so mkdir(parents=True) fails with a real OSError.
        blocking_file = tmp_path / "blocking"
        blocking_file.write_text("not a directory")
        output_path = blocking_file / "collection.json"

        with pytest.raises(RuntimeError, match="Failed to write file"):
            ec.write_file(data=valid_collection(), output_path=output_path)


# ---------------------------------------------------------------------------
# export_collections
# ---------------------------------------------------------------------------

class TestExportCollections:
    def test_writes_a_file_per_collection(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.setattr(ec, "OUTPUT_DIR", tmp_path)

        def _filename_from_uid(*, collection: CollectionResponse) -> str:
            return collection["collection"]["uid"]

        monkeypatch.setattr(ec, "generate_filename", _filename_from_uid)

        write_mock = MagicMock()
        monkeypatch.setattr(ec, "write_file", write_mock)

        collections = [valid_collection(uid="uid-1"), valid_collection(uid="uid-2")]
        ec.export_collections(fetched_collections=collections)

        assert write_mock.call_count == 2
        write_mock.assert_any_call(data=collections[0], output_path=tmp_path / "uid-1.json")
        write_mock.assert_any_call(data=collections[1], output_path=tmp_path / "uid-2.json")

    def test_no_collections_writes_nothing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        write_mock = MagicMock()
        monkeypatch.setattr(ec, "write_file", write_mock)

        ec.export_collections(fetched_collections=[])

        write_mock.assert_not_called()

    def test_one_bad_collection_does_not_abort_the_batch(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setattr(ec, "OUTPUT_DIR", tmp_path)

        good = valid_collection(uid="uid-good")
        bad = malformed_collection({"collection": {"info": {"name": "", "uid": ""}, "name": "", "uid": ""}})

        write_mock = MagicMock()
        monkeypatch.setattr(ec, "write_file", write_mock)

        def _generate_filename_maybe_failing(*, collection: CollectionResponse) -> str:
            if collection is bad:
                raise ValueError("bad data")
            return "uid-good_TS"

        monkeypatch.setattr(ec, "generate_filename", _generate_filename_maybe_failing)

        ec.export_collections(fetched_collections=[bad, good])

        # The good collection still got written despite the bad one failing.
        write_mock.assert_called_once_with(data=good, output_path=tmp_path / "uid-good_TS.json")

        captured = capsys.readouterr()
        assert "Failed to export collection" in captured.err
        assert "Exported 1/2" in captured.err

    def test_write_failure_is_logged_not_raised(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setattr(ec, "OUTPUT_DIR", tmp_path)

        def _fixed_filename(*, collection: CollectionResponse) -> str:
            _ = collection
            return "name_TS"

        monkeypatch.setattr(ec, "generate_filename", _fixed_filename)
        monkeypatch.setattr(ec, "write_file", MagicMock(side_effect=RuntimeError("disk full")))

        # Should not raise.
        ec.export_collections(fetched_collections=[valid_collection(uid="uid-1")])

        captured = capsys.readouterr()
        assert "disk full" in captured.err

    def test_end_to_end_writes_real_file(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Integration-style test using the real generate_filename/write_file (no mocking either)."""
        monkeypatch.setattr(ec, "OUTPUT_DIR", tmp_path)

        def _sanitize(*, text: str) -> str:
            return text.replace(" ", "-")

        def _get_datetime() -> str:
            return "TS"

        monkeypatch.setattr(ec, "sanitize", _sanitize) 
        monkeypatch.setattr(ec, "get_datetime", _get_datetime) 

        collections = [valid_collection(name="My Collection", uid="uid-1")]
        ec.export_collections(fetched_collections=collections)

        expected_file = tmp_path / "My-Collection_TS.json"
        assert expected_file.exists()
        written: JSON = json.loads(expected_file.read_text(encoding="utf-8"))
        assert written == collections[0]


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

class TestMain:
    def test_main_is_a_noop(self) -> None:
        assert ec.main() is None
