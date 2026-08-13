from pathlib import Path
from unittest.mock import MagicMock, patch

from src.schema import CollectionResponse

# from src.postman_api.export_collections import (
#     fetch_collection,
#     generate_filename,
#     resolve_and_fetch_collections,
#     write_file,
# )


class TestFetchCollection:
    @patch("src.postman_api.export_collections.requests.get")
    def test_fetches_by_uid(
        self,
        mock_get: MagicMock,
        sample_collection_response: CollectionResponse,
    ) -> None:
        # TODO: mock_get.return_value.json.return_value = sample_collection_response
        # TODO: assert fetch_collection(collection_uid="12345-sample-uid") == sample_collection_response
        pass


class TestResolveAndFetchCollections:
    def test_accepts_single_uid_string(self) -> None:
        # TODO: assert a single str uid resolves to a one-item list
        pass

    def test_accepts_list_of_uids(self) -> None:
        # TODO: assert a list[str] resolves to one fetch per uid
        pass


class TestGenerateFilename:
    def test_uses_sanitized_collection_name(self, sample_collection_response: CollectionResponse) -> None:
        # TODO: assert generate_filename(...) starts with the sanitized name
        pass

    def test_falls_back_to_uid_when_name_missing(self) -> None:
        # TODO: build a CollectionResponse with an empty name, assert uid is used instead
        pass


class TestWriteFile:
    def test_writes_valid_json(self, tmp_path: Path, sample_collection_response: CollectionResponse) -> None:
        # TODO: write_file(data=sample_collection_response, output_path=tmp_path / "out.json")
        # TODO: read it back with json.load and assert it round-trips
        pass
