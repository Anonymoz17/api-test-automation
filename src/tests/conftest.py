import pytest

from src.schema import CollectionData, CollectionInfo, CollectionResponse


@pytest.fixture
def sample_collection_info() -> CollectionInfo:
    return {"name": "Sample Collection", "uid": "12345-sample-uid"}


@pytest.fixture
def sample_collection_data(sample_collection_info: CollectionInfo) -> CollectionData:
    return {
        "info": sample_collection_info,
        "name": sample_collection_info["name"],
        "uid": sample_collection_info["uid"],
    }


@pytest.fixture
def sample_collection_response(sample_collection_data: CollectionData) -> CollectionResponse:
    return {
        "collection": sample_collection_data,
        "collections": [sample_collection_data],
    }
