import json
from pathlib import Path
from typing import cast

import requests
from requests.models import Response

from src.config import POSTMAN_API_BASE_URL, POSTMAN_API_HEADERS, PROJECT_ROOT
from src.schema import CollectionResponse
from src.utils.helper import get_datetime, sanitize

TARGET_URL: str = POSTMAN_API_BASE_URL + "/collections"

OUTPUT_DIR: Path = (PROJECT_ROOT / "exports").resolve()
FILE_EXTENSION: str = "json"


def fetch_collection(collection_uid: str) -> CollectionResponse:
    """fetches/exports a single collection using the collection uid"""

    response: Response = requests.get(url=TARGET_URL + "/" + collection_uid, headers=POSTMAN_API_HEADERS)
    collection: CollectionResponse = cast(CollectionResponse, response.json())

    return collection


def resolve_and_fetch_collections(collection_uids: str | list[str]) -> list[CollectionResponse]:
    """Resolves whether input is a single or list of collections. Then outputs responses in a list"""

    uid_list: list[str] = [collection_uids] if isinstance(collection_uids, str) else collection_uids
    return [fetch_collection(collection_uid=uid) for uid in uid_list]


def generate_filename(collection: CollectionResponse) -> str:
    """Generate filename based on collection's name or collection uid with datetime appended"""

    name: str = ""

    if (collection["collection"]["info"]["name"]):
        name = sanitize(text=collection["collection"]["info"]["name"])
    else: 
        name = collection["collection"]["info"]["uid"]

    name += f"_{get_datetime()}"

    return name


# Write response(collection) into JSON file
def write_file(data: CollectionResponse, output_path: Path) -> None:
    """Writes file to path"""

    with open(file=output_path, mode="w", encoding="utf-8") as f:
        json.dump(obj=data, fp=f, indent=4)


def export_collections(fetched_collections: list[CollectionResponse]) -> None:
    """Exports collections by fetching from Postman API and writing the files to path"""

    for collection in fetched_collections:
        file_name: str      = generate_filename(collection=collection)
        output_path: Path   = OUTPUT_DIR / f"{file_name}.{FILE_EXTENSION}"
        write_file(data=collection, output_path=output_path)


def main() -> None:
    pass

if __name__ == "__main__":
    main()
