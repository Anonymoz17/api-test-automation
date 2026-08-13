from typing import cast

import requests
from requests import Response

from src.config import (
    POSTMAN_API_BASE_URL,
    POSTMAN_API_HEADERS,
    POSTMAN_API_WORKSPACE_UID,
)
from src.schema import CollectionResponse


def get_all_collections() -> CollectionResponse:
    response: Response = requests.get(url=f"{POSTMAN_API_BASE_URL}/collections",
                                      params={"workspace":{POSTMAN_API_WORKSPACE_UID}},
                                      headers=POSTMAN_API_HEADERS)
    response_data: CollectionResponse = cast(CollectionResponse, response.json())

    return response_data


def get_collection_uids(collections: CollectionResponse) -> list[str]:
    collection_uids_list: list[str] = []

    for item in collections["collections"]:
        collection_uids_list.append(item["uid"])

    return collection_uids_list


def main():
    collections = get_all_collections()
    print(get_collection_uids(collections))
    print(len(collections["collections"]))


if __name__ == "__main__":
    main()
