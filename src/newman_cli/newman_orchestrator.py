"""
Runs a Postman collection through the Newman CLI and stores the report
in newman-runs/. Backs the `run` subcommand in src/main.py.
"""

import json
import shutil
import subprocess
from pathlib import Path
from typing import cast

from src.config import PROJECT_ROOT
from src.schema import NewmanConfig, ReporterConfig
from src.utils.helper import get_datetime, sanitize

NEWMAN_EXECUTABLE: str  = "newman"

OUTPUT_DIR: Path        = (PROJECT_ROOT / "newman-runs").resolve()
FILE_EXTENSION: str     = "json"


def load_newman_config(config_path: Path) -> NewmanConfig:
    """Loads a Newman run config (see schema.NewmanConfig) from a JSON file."""

    if config_path.suffix.lower() != f".{FILE_EXTENSION}":
        raise ValueError(f"Expected a .{FILE_EXTENSION} file, got: {config_path}")

    with open(file=config_path, mode="r", encoding="utf-8") as f:
        return cast(NewmanConfig, json.load(f))


def is_newman_installed() -> bool:
    """Checks that the `newman` executable is reachable on PATH."""

    return shutil.which(NEWMAN_EXECUTABLE) is not None


def generate_run_filename(collection_path: Path) -> str:
    """Builds a timestamped report filename from the collection's file name."""

    name: str = sanitize(text=collection_path.stem)
    name += f"_{get_datetime()}"

    return name


def reporter_args(config: NewmanConfig) -> list[str]:
    args: list[str] = ["--reporters"]
    reporter_types: list[str] = ["cli"]

    reporter: ReporterConfig | None = config.get("reporter")

    if not reporter:
        args.append(reporter_types[0])
        return args

    #TODO: sanitize file path
    if "json" in reporter:
        args += [
            "--reporter-json-export",
            str(Path(reporter["json"])),
        ]
        reporter_types += ["json"]

    args.insert(1, ",".join(reporter_types))

    return args


def build_newman_command(config: NewmanConfig) -> list[str]:    
    """Assembles the `newman run` argv.
    TODO: add any extra flags you need, e.g. --bail, --iteration-data,
    --global-var, --insecure, etc. (see `newman run --help`).
    """

    collection: str | None = config.get("collection")
    environment: str | None = config.get("environment")

    if not collection:
        raise ValueError("config['collection'] is required")

    command: list[str] = [
        "newman",
        "run",
        collection,
    ]

    if environment:
        command += [
            "-e",
            environment
        ]

    command += reporter_args(config=config)

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
