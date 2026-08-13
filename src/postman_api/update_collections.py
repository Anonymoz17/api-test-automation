"""
Loads Collection json file and uses the "uid" value to update the Collection
along with its contents using the Postman API.
"""

import json
from pathlib import Path
from typing import cast

import requests
from requests.models import Response

from src.config import POSTMAN_API_BASE_URL, POSTMAN_API_HEADERS
from src.schema import JSON, CollectionResponse

FILE_EXTENSION: str = "json"


# load Collection json file as CollectionResponse type
def load_collection_file(collection_file_path: Path) -> CollectionResponse:
    with open(file=collection_file_path, mode="r", encoding="utf-8") as f:
        return cast(CollectionResponse, json.load(f))


def get_collection_uid(collection_data: CollectionResponse) -> str:
    return collection_data["collection"]["info"]["uid"]


def update_collection(collection_file_path: Path) -> CollectionResponse:
    """Updates a single collection"""

    collection_data: CollectionResponse = load_collection_file(collection_file_path=collection_file_path)
    collection_uid: str                 = get_collection_uid(collection_data=collection_data)

    response: Response = requests.put(
        url=f"{POSTMAN_API_BASE_URL}/collections/{collection_uid}",
        headers={
            **POSTMAN_API_HEADERS,
            "Content-Type": "application/json",
        },
        json=cast(JSON, cast(object, collection_data))
    )

    response.raise_for_status()

    return cast(CollectionResponse, response.json())

def resolve_collection_files(path: Path) -> list[Path]:
    if path.is_file():
        if path.suffix.lower() != f".{FILE_EXTENSION}":
            raise ValueError(f"Expected a .{FILE_EXTENSION} file, got: {path}")
        return [path]

    if path.is_dir():
        return sorted(path.glob(f"*.{FILE_EXTENSION}"))

    raise FileNotFoundError(f"Path does not exist: {path}")


def resolve_and_update_collections(collections_path: Path) -> list[CollectionResponse]:
    collection_files: list[Path] = resolve_collection_files(collections_path)
    return [update_collection(collection_file_path=file) for file in collection_files]


def main():
    directory: Path = Path("path").expanduser()
    _ = update_collection(Path(directory))


if __name__ == "__main__":
    main()
