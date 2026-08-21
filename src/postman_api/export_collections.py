import json
import sys
from pathlib import Path
from typing import cast

import requests
from requests.models import Response

from src.env import POSTMAN_API_BASE_URL, POSTMAN_API_HEADERS, PROJECT_ROOT
from src.schema import JSON, CollectionInfo, CollectionResponse
from src.utils.helper import get_datetime, sanitize

TARGET_URL: str     = POSTMAN_API_BASE_URL + "/collections"
OUTPUT_DIR: Path    = (PROJECT_ROOT / "postman_exports").resolve()
FILE_EXTENSION: str = "json"
REQUEST_TIMEOUT_SECONDS: int = 30


def fetch_collection(collection_uid: str) -> CollectionResponse:
    """Fetches/exports a single collection using the collection uid.

    Raises:
        RuntimeError: if the request fails (network/timeout), the response
            body isn't valid JSON, or the payload isn't a usable collection.
    """
    try:
        response: Response = requests.get(
            url=TARGET_URL + "/" + collection_uid,
            headers=POSTMAN_API_HEADERS,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(
            f"Failed to fetch collection '{collection_uid}': network error ({exc})"
        ) from exc

    try:
        body: JSON = response.json()
    except ValueError as exc:
        raise RuntimeError(
            f"Failed to fetch collection '{collection_uid}' "
            + f"(status {response.status_code}): response was not valid JSON"
        ) from exc

    if not isinstance(body, dict) or not response.ok or "collection" not in body:
        error_detail: JSON = body.get("error", body) if isinstance(body, dict) else body
        raise RuntimeError(
            f"Failed to fetch collection '{collection_uid}' "
            + f"(status {response.status_code}): {error_detail}"
        )

    return cast(CollectionResponse, cast(object, body))


def resolve_and_fetch_collections(collection_uids: str | list[str]) -> list[CollectionResponse]:
    """Resolves whether input is a single or list of collections. Then outputs responses in a list.

    Raises:
        ValueError: if no collection uids were provided.
    """
    uid_list: list[str] = [collection_uids] if isinstance(collection_uids, str) else collection_uids

    if not uid_list:
        raise ValueError("No collection UIDs provided to fetch")

    return [fetch_collection(collection_uid=uid) for uid in uid_list]


def generate_filename(collection: CollectionResponse) -> str:
    """Generate filename based on collection's name or collection uid with datetime appended.

    Raises:
        ValueError: if the collection has neither a usable name nor a uid.
    """
    info: CollectionInfo = collection.get("collection", {}).get("info", {})
    name: str = ""

    raw_name = info.get("name")
    if raw_name:
        name = sanitize(text=raw_name)

    if not name:
        uid = info.get("uid")
        if not uid:
            raise ValueError("Collection has neither a usable name nor a uid to build a filename from")
        name = uid

    return f"{name}_{get_datetime()}"


def write_file(data: CollectionResponse, output_path: Path) -> None:
    """Writes file to path, creating parent directories if they don't exist.

    Raises:
        RuntimeError: if the file can't be written (permissions, disk full, etc).
    """
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file=output_path, mode="w", encoding="utf-8") as f:
            json.dump(obj=data, fp=f, indent=4)
    except OSError as exc:
        raise RuntimeError(f"Failed to write file '{output_path}': {exc}") from exc


def export_collections(fetched_collections: list[CollectionResponse]) -> None:
    """Exports collections by writing each fetched collection to disk.

    A failure on one collection (bad filename data, disk error, etc.) is
    logged and does not abort the rest of the batch.
    """
    failures: list[str] = []

    for collection in fetched_collections:
        uid: str = collection.get("collection", {}).get("uid", "<unknown>")
        try:
            file_name: str    = generate_filename(collection=collection)
            output_path: Path = OUTPUT_DIR / f"{file_name}.{FILE_EXTENSION}"
            write_file(data=collection, output_path=output_path)
        except (ValueError, RuntimeError) as exc:
            print(f"Failed to export collection '{uid}': {exc}", file=sys.stderr)
            failures.append(uid)

    if failures:
        succeeded = len(fetched_collections) - len(failures)
        print(
            f"Exported {succeeded}/{len(fetched_collections)} collection(s); "
            + f"failed: {', '.join(failures)}",
            file=sys.stderr,
        )


def main() -> None:
    pass


if __name__ == "__main__":
    main()
