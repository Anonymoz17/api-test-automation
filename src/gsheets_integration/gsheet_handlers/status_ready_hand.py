"""
Reads a Newman JSON run report and syncs response-code / status info into
a Google Sheet for job hand-off tracking. Backs the `status` step invoked
after a Newman run completes.
"""
import json
import logging
from typing import cast

from gspread import Spreadsheet, Worksheet

from src.schema import JSON

logger: logging.Logger = logging.getLogger(__name__)

COL_STATUS_CODE: int = 7   # column G
COL_DEVELOPER_MESSAGE: int = 9  # column I

NOT_IMPLEMENTED_MESSAGE: str = "The operation has not been implemented"
NOT_IMPLEMENTED_LABEL: str = "Not Implemented"


def _as_dict(value: JSON, context: str) -> dict[str, JSON]:
    """Narrows a JSON value to dict[str, JSON], raising with useful context
    if the report doesn't match Newman's expected shape.
    """
    if not isinstance(value, dict):
        raise TypeError(f"expected '{context}' to be a JSON object, got {type(value).__name__}")
    return cast(dict[str, JSON], value)


def _as_list(value: JSON, context: str) -> list[JSON]:
    """Narrows a JSON value to list[JSON], raising with useful context if
    the report doesn't match Newman's expected shape.
    """
    if not isinstance(value, list):
        raise TypeError(f"expected '{context}' to be a JSON array, got {type(value).__name__}")
    return value


def _as_str(value: JSON, context: str) -> str:
    """Narrows a JSON value to str, raising with useful context if the
    report doesn't match Newman's expected shape.
    """
    if not isinstance(value, str):
        raise TypeError(f"expected '{context}' to be a string, got {type(value).__name__}")
    return value


def _find_header_value(headers: JSON, key: str) -> str | None:
    """Finds a header's value by key (case-insensitive) in a Postman
    response['header'] list, which is shaped like:
        [{"key": "Content-Type", "value": "application/json"}, ...]
    """
    if not isinstance(headers, list):
        return None

    for header in headers:
        if not isinstance(header, dict):
            continue
        header_key = header.get("key")
        if isinstance(header_key, str) and header_key.lower() == key.lower():
            value = header.get("value")
            return value if isinstance(value, str) else None

    return None


def _parse_json_body(response: dict[str, JSON]) -> JSON | None:
    """Parses response['stream'] (a Newman byte-array buffer) into JSON,
    but only if the response's content-type header is application/json.
    Returns None if the content type doesn't match or parsing fails.
    """
    content_type = _find_header_value(response.get("header"), "content-type")
    if content_type is None or "application/json" not in content_type.lower():
        return None

    stream = response.get("stream")
    if not isinstance(stream, dict):
        return None

    data = stream.get("data")
    if not isinstance(data, list):
        return None

    if not all(isinstance(item, int) for item in data):
        return None
    byte_values: list[int] = cast(list[int], data)

    try:
        raw_bytes = bytes(byte_values)
        decoded = raw_bytes.decode("utf-8")
        parsed: JSON = json.loads(decoded)
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        logger.warning("Failed to parse response stream as JSON: %s", exc)
        return None

    return parsed


def _developer_message_label(body: JSON) -> str | None:
    """Maps a parsed JSON response body's top-level 'developerMessage' to a
    sheet-friendly label. Returns None if there's no matching message.
    """
    if not isinstance(body, dict):
        return None

    developer_message = body.get("developerMessage")
    if developer_message == NOT_IMPLEMENTED_MESSAGE:
        return NOT_IMPLEMENTED_LABEL

    return None


def _build_row_lookup(rows: list[list[str]]) -> dict[tuple[str, str], int]:
    """Builds a (collection_name, request_name) -> sheet row number lookup
    from column A and D, so each execution can be matched in O(1).
    """
    row_lookup: dict[tuple[str, str], int] = {}
    for row_index, row in enumerate(rows[1:], start=2):  # sheet rows are 1-indexed, skip header
        col_a = row[0] if len(row) > 0 else ""
        col_d = row[3] if len(row) > 3 else ""
        row_lookup[(col_a, col_d)] = row_index

    return row_lookup


def _cell_value(row: list[str], col_index: int) -> str:
    """Safely reads a 1-indexed column value from a sheet row, defaulting
    to "" if the row is shorter than expected.
    """
    zero_based = col_index - 1
    return row[zero_based] if len(row) > zero_based else ""


def update(newman_run_report: JSON, _spreadsheet: Spreadsheet, worksheet: Worksheet) -> None:
    """Updates col G (status code) and col I (developer message label) for
    each execution's request, matched to a row by col A (collection name)
    and col D (request name).

    `_spreadsheet` is currently unused (the worksheet is looked up and
    passed in by the caller already) but kept in the signature to match
    the shared `update(report, spreadsheet, worksheet)` interface used
    across sync steps.
    """
    report: dict[str, JSON] = _as_dict(newman_run_report, "newman_run_report")
    collection: dict[str, JSON] = _as_dict(report["collection"], "collection")
    info: dict[str, JSON] = _as_dict(collection["info"], "collection.info")
    collection_name: str = _as_str(info["name"], "collection.info.name")

    run: dict[str, JSON] = _as_dict(report["run"], "run")
    executions: list[JSON] = _as_list(run["executions"], "run.executions")

    logger.info("Syncing %d execution(s) for collection '%s'", len(executions), collection_name)

    rows: list[list[str]] = worksheet.get_all_values()  # row 0 = header
    row_lookup = _build_row_lookup(rows)

    updated_count = 0
    skipped_count = 0

    for index, execution_raw in enumerate(executions):
        execution = _as_dict(execution_raw, f"run.executions[{index}]")
        item = _as_dict(execution["item"], f"run.executions[{index}].item")
        request_name = _as_str(item["name"], f"run.executions[{index}].item.name")

        response = _as_dict(execution["response"], f"run.executions[{index}].response")
        status_code = response["code"]

        row_number = row_lookup.get((collection_name, request_name))
        if row_number is None:
            logger.warning("No matching row for request '%s', skipping", request_name)
            skipped_count += 1
            continue

        row = rows[row_number - 1]

        # --- status code (col G) ---
        new_status_value = str(status_code)
        if _cell_value(row, COL_STATUS_CODE) != new_status_value:
            _ = worksheet.update_cell(row_number, COL_STATUS_CODE, new_status_value)
            updated_count += 1

        # --- developer message label (col I) ---
        body = _parse_json_body(response)
        label = _developer_message_label(body)
        if label is not None and _cell_value(row, COL_DEVELOPER_MESSAGE) != label:
            _ = worksheet.update_cell(row_number, COL_DEVELOPER_MESSAGE, label)
            updated_count += 1

    logger.info(
        "Sheet sync complete: %d cell(s) updated, %d request(s) skipped (no matching row)",
        updated_count,
        skipped_count,
    )
