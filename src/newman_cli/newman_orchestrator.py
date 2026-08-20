"""
Runs a Postman collection through the Newman CLI and stores the report
in newman-runs/. Backs the `run` subcommand in src/main.py.
"""

import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import cast

from src.env import PROJECT_ROOT
from src.schema import JSON, NewmanConfig, ReporterConfig
from src.utils.helper import get_datetime, sanitize

NEWMAN_EXECUTABLE: str  = "newman"

OUTPUT_DIR: Path        = (PROJECT_ROOT / "newman_runs").resolve()
FILE_EXTENSION: str     = "json"


def load_newman_config(config_path: Path) -> NewmanConfig:
    """Loads a Newman run config (see schema.NewmanConfig) from a JSON file."""

    if config_path.suffix.lower() != f".{FILE_EXTENSION}":
        raise ValueError(f"Expected a .{FILE_EXTENSION} file, got: {config_path}")

    with open(file=config_path, mode="r", encoding="utf-8") as f:
        return cast(NewmanConfig, json.load(f))


def inject_test_script(collection_path: Path, script_path: Path) -> Path:
    """
    Injects a collection-level `test` event built from a JS file into the
    Postman collection at collection_path, and writes the result to a
    temp file for newman to run against. Not persisted anywhere in the
    project — the caller is expected to delete it once the run finishes.
    """
    if not script_path.is_file():
        raise FileNotFoundError(f"Test script not found: {script_path}")
    with open(file=collection_path, mode="r", encoding="utf-8") as f:
        collection: dict[str, JSON] = cast(dict[str, JSON], json.load(f))
    postman_collection: dict[str, JSON] = cast(dict[str, JSON], collection["collection"])
    script_lines: list[str] = script_path.read_text(encoding="utf-8").splitlines()
    test_event: dict[str, JSON] = {
        "listen": "test",
        "script": {
            "type": "text/javascript",
            "exec": cast(JSON, script_lines),
        },
    }
    existing_events: list[JSON] = cast(list[JSON], postman_collection.get("event", []))
    remaining_events: list[JSON] = [
        event for event in existing_events
        if not (isinstance(event, dict) and event.get("listen") == "test")
    ]
    remaining_events.append(cast(JSON, test_event))
    postman_collection["event"] = cast(JSON, remaining_events)

    output_name: str = generate_run_filename(collection_path=collection_path, kind="test")
    output_path: Path = Path(tempfile.gettempdir()) / f"{output_name}.{FILE_EXTENSION}"
    with open(file=output_path, mode="w", encoding="utf-8") as f:
        json.dump(obj=collection, fp=f, indent=4)
    return output_path


def is_newman_installed() -> bool:
    """Checks that the `newman` executable is reachable on PATH."""

    return shutil.which(NEWMAN_EXECUTABLE) is not None


def generate_run_filename(collection_path: Path, kind: str) -> str:
    """Builds a labeled, timestamped filename from the collection's file name.
    e.g. kind="test" -> {collection_name}_test_{datetime}
         kind="run"  -> {collection_name}_run_{datetime}
    """
    name: str = sanitize(text=collection_path.stem)
    return f"{name}_{kind}_{get_datetime()}"


def report_path_for(collection: str) -> Path:
    """Derives a timestamped JSON report path from the collection file name.
    Mints a new timestamp on every call — compute this ONCE per run and
    reuse the result; calling it twice for the same run yields two
    different paths.
    """
    name: str = generate_run_filename(collection_path=Path(collection), kind="run")
    return OUTPUT_DIR / f"{name}.{FILE_EXTENSION}"

def reporter_args(config: NewmanConfig, report_path: Path | None) -> list[str]:
    args: list[str] = ["--reporters"]
    reporter_types: list[str] = ["cli"]
    reporter: ReporterConfig | None = config.get("reporter")
    if not reporter:
        args.append(reporter_types[0])
        return args
    if reporter.get("json"):
        if report_path is None:
            raise ValueError("report_path is required when reporter['json'] is true")
        report_path.parent.mkdir(parents=True, exist_ok=True)
        args += [
            "--reporter-json-export",
            str(report_path),
        ]
        reporter_types += ["json"]
    args.insert(1, ",".join(reporter_types))
    return args


def build_newman_command(config: NewmanConfig, report_path: Path | None = None) -> list[str]:
    collection: str | None = config.get("collection")
    environment: str | None = config.get("environment")
    if not collection:
        raise ValueError("config['collection'] is required")
    command: list[str] = ["newman", "run", collection]
    if environment:
        command += ["-e", environment]
    command += reporter_args(config=config, report_path=report_path)
    return command


def run_newman(command: list[str]) -> subprocess.CompletedProcess[str]:
    """Executes the assembled newman command."""

    if not is_newman_installed():
        raise FileNotFoundError(
            f"'{NEWMAN_EXECUTABLE}' not found on PATH; is Newman installed?"
        )

    try:
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        raise RuntimeError(f"Failed to execute newman command: {command!r}") from exc


def main() -> None:
    raise NotImplementedError


if __name__ == "__main__":
    main()
