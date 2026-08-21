"""
Tests for newman_orchestrator.py
"""
import json
import subprocess
from pathlib import Path
from typing import cast

import pytest
from pytest import MonkeyPatch

from src.newman_cli.newman_orchestrator import (
    build_newman_command,
    generate_run_filename,
    inject_test_script,
    is_newman_installed,
    load_newman_config,
    report_path_for,
    reporter_args,
    run_newman,
)
from src.schema import JSON, NewmanConfig, ReporterConfig

# ---------------------------------------------------------------------------
# load_newman_config
# ---------------------------------------------------------------------------

def test_load_newman_config_reads_valid_json(tmp_path: Path) -> None:
    config_path: Path = tmp_path / "config.json"
    _ = config_path.write_text(json.dumps({"collection": "collection.json"}), encoding="utf-8")

    config: NewmanConfig = load_newman_config(config_path)

    assert config.get("collection") == "collection.json"


def test_load_newman_config_rejects_non_json_extension(tmp_path: Path) -> None:
    config_path: Path = tmp_path / "config.yaml"
    _ = config_path.write_text("collection: collection.json", encoding="utf-8")

    with pytest.raises(ValueError, match=r"Expected a \.json file"):
        _ = load_newman_config(config_path)


def test_load_newman_config_raises_on_missing_file(tmp_path: Path) -> None:
    missing_path: Path = tmp_path / "missing.json"

    with pytest.raises(FileNotFoundError):
        _ = load_newman_config(missing_path)


# ---------------------------------------------------------------------------
# inject_test_script
# ---------------------------------------------------------------------------

def test_inject_test_script_raises_when_script_missing(tmp_path: Path) -> None:
    collection_path: Path = tmp_path / "collection.json"
    _ = collection_path.write_text(json.dumps({"collection": {"event": []}}), encoding="utf-8")
    missing_script: Path = tmp_path / "missing.js"

    with pytest.raises(FileNotFoundError):
        _ = inject_test_script(collection_path, missing_script)


def test_inject_test_script_appends_test_event(tmp_path: Path) -> None:
    collection_path: Path = tmp_path / "collection.json"
    collection_data: dict[str, JSON] = {
        "collection": {
            "info": {"name": "My Collection"},
            "event": [],
        }
    }
    _ = collection_path.write_text(json.dumps(collection_data), encoding="utf-8")

    script_path: Path = tmp_path / "test_script.js"
    _ = script_path.write_text("pm.test('ok', () => {});", encoding="utf-8")

    output_path: Path = inject_test_script(collection_path, script_path)

    assert output_path.exists()
    written: dict[str, JSON] = cast(
        dict[str, JSON], json.loads(output_path.read_text(encoding="utf-8"))
    )
    postman_collection = cast(dict[str, JSON], written["collection"])
    events = cast(list[JSON], postman_collection["event"])

    assert len(events) == 1
    injected_event = cast(dict[str, JSON], events[0])
    assert injected_event["listen"] == "test"


def test_inject_test_script_replaces_existing_test_event(tmp_path: Path) -> None:
    collection_path: Path = tmp_path / "collection.json"
    collection_data: dict[str, JSON] = {
        "collection": {
            "info": {"name": "My Collection"},
            "event": [
                {"listen": "test", "script": {"exec": ["old script"]}},
                {"listen": "prerequest", "script": {"exec": ["keep me"]}},
            ],
        }
    }
    _ = collection_path.write_text(json.dumps(collection_data), encoding="utf-8")

    script_path: Path = tmp_path / "test_script.js"
    _ = script_path.write_text("pm.test('new', () => {});", encoding="utf-8")

    output_path: Path = inject_test_script(collection_path, script_path)

    written: dict[str, JSON] = cast(
        dict[str, JSON], json.loads(output_path.read_text(encoding="utf-8"))
    )
    postman_collection = cast(dict[str, JSON], written["collection"])
    events = cast(list[JSON], postman_collection["event"])

    # old "test" event replaced, "prerequest" event untouched, new "test" appended
    assert len(events) == 2
    listens = [cast(dict[str, JSON], e)["listen"] for e in events]
    assert listens.count("test") == 1
    assert "prerequest" in listens


# ---------------------------------------------------------------------------
# is_newman_installed
# ---------------------------------------------------------------------------

def test_is_newman_installed_true_when_on_path(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr("shutil.which", lambda _: "/usr/local/bin/newman")
    assert is_newman_installed() is True


def test_is_newman_installed_false_when_missing(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr("shutil.which", lambda _: None)
    assert is_newman_installed() is False


# ---------------------------------------------------------------------------
# generate_run_filename / report_path_for
# ---------------------------------------------------------------------------

def test_generate_run_filename_includes_kind_and_sanitized_name(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr("src.newman_cli.newman_orchestrator.sanitize", lambda text: "clean_name")
    monkeypatch.setattr("src.newman_cli.newman_orchestrator.get_datetime", lambda: "20260821")

    result: str = generate_run_filename(Path("My Collection.json"), kind="run")

    assert result == "clean_name_run_20260821"


def test_report_path_for_builds_json_path_in_output_dir(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr("src.newman_cli.newman_orchestrator.sanitize", lambda text: "clean_name")
    monkeypatch.setattr("src.newman_cli.newman_orchestrator.get_datetime", lambda: "20260821")

    result: Path = report_path_for("collection.json")

    assert result.name == "clean_name_run_20260821.json"


# ---------------------------------------------------------------------------
# reporter_args
# ---------------------------------------------------------------------------

def test_reporter_args_defaults_to_cli_only() -> None:
    config: NewmanConfig = cast(NewmanConfig, cast(object, {"collection": "collection.json"}))

    args: list[str] = reporter_args(config, report_path=None)

    assert args == ["--reporters", "cli"]


def test_reporter_args_adds_json_export_when_requested(tmp_path: Path) -> None:
    reporter: ReporterConfig = cast(ReporterConfig, cast(object, {"json": True}))
    config: NewmanConfig = cast(
        NewmanConfig, cast(object, {"collection": "collection.json", "reporter": reporter}
    ))
    report_path: Path = tmp_path / "reports" / "run.json"

    args: list[str] = reporter_args(config, report_path=report_path)

    assert args[0] == "--reporters"
    assert "cli,json" in args
    assert "--reporter-json-export" in args
    assert str(report_path) in args
    assert report_path.parent.is_dir()


def test_reporter_args_raises_when_json_requested_without_path() -> None:
    reporter: ReporterConfig = cast(ReporterConfig, cast(object, {"json": True}))
    config: NewmanConfig = cast(
        NewmanConfig, cast(object, {"collection": "collection.json", "reporter": reporter}
    ))

    with pytest.raises(ValueError, match="report_path is required"):
        _ = reporter_args(config, report_path=None)


# ---------------------------------------------------------------------------
# build_newman_command
# ---------------------------------------------------------------------------

def test_build_newman_command_requires_collection() -> None:
    config: NewmanConfig = cast(NewmanConfig, cast(object, {}))

    with pytest.raises(ValueError, match="config\\['collection'\\] is required"):
        _ = build_newman_command(config)


def test_build_newman_command_includes_environment_when_present() -> None:
    config: NewmanConfig = cast(
        NewmanConfig, cast(object, {"collection": "collection.json", "environment": "env.json"}
    ))

    command: list[str] = build_newman_command(config)

    assert command[:3] == ["newman", "run", "collection.json"]
    assert "-e" in command
    assert "env.json" in command


def test_build_newman_command_omits_environment_when_absent() -> None:
    config: NewmanConfig = cast(NewmanConfig, cast(object, {"collection": "collection.json"}))

    command: list[str] = build_newman_command(config)

    assert "-e" not in command


# ---------------------------------------------------------------------------
# run_newman
# ---------------------------------------------------------------------------

def test_run_newman_raises_when_newman_not_installed(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr("src.newman_cli.newman_orchestrator.is_newman_installed", lambda: False)

    with pytest.raises(FileNotFoundError, match="not found on PATH"):
        _ = run_newman(["newman", "run", "collection.json"])


def test_run_newman_returns_completed_process_on_success(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr("src.newman_cli.newman_orchestrator.is_newman_installed", lambda: True)

    expected: subprocess.CompletedProcess[str] = subprocess.CompletedProcess(
        args=["newman", "run", "collection.json"],
        returncode=0,
        stdout="ok",
        stderr="",
    )
    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: expected)

    result: subprocess.CompletedProcess[str] = run_newman(["newman", "run", "collection.json"])

    assert result.returncode == 0


def test_run_newman_wraps_oserror_in_runtimeerror(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr("src.newman_cli.newman_orchestrator.is_newman_installed", lambda: True)

    def _raise_oserror(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise OSError("boom")

    monkeypatch.setattr("subprocess.run", _raise_oserror)

    with pytest.raises(RuntimeError, match="Failed to execute newman command"):
        _ = run_newman(["newman", "run", "collection.json"])
