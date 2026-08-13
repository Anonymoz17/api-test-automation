from pathlib import Path
from unittest.mock import MagicMock, patch

from src.schema import CollectionResponse

# from src.postman_api.update_collections import (
#     get_collection_uid,
#     load_collection_file,
#     resolve_collection_files,
#     update_collection,
# )


class TestLoadCollectionFile:
    def test_loads_json_file_as_collection_response(
        self,
        tmp_path: Path,
        sample_collection_response: CollectionResponse,
    ) -> None:
        # TODO: write sample_collection_response to a tmp_path file with json.dump
        # TODO: assert load_collection_file(...) == sample_collection_response
        pass


class TestGetCollectionUid:
    def test_extracts_uid_from_collection_info(self, sample_collection_response: CollectionResponse) -> None:
        # TODO: assert get_collection_uid(sample_collection_response) == "12345-sample-uid"
        pass


class TestResolveCollectionFiles:
    def test_single_json_file_returns_itself(self, tmp_path: Path) -> None:
        # TODO: create a .json file, assert resolve_collection_files(file) == [file]
        pass

    def test_non_json_file_raises_value_error(self, tmp_path: Path) -> None:
        # TODO: create a .txt file, assert resolve_collection_files(file) raises ValueError
        pass

    def test_directory_returns_sorted_json_files(self, tmp_path: Path) -> None:
        # TODO: create multiple .json files (and a non-.json file to ignore),
        #       assert resolve_collection_files(dir) returns only the sorted .json ones
        pass

    def test_missing_path_raises_file_not_found(self, tmp_path: Path) -> None:
        # TODO: assert resolve_collection_files(tmp_path / "missing") raises FileNotFoundError
        pass


class TestUpdateCollection:
    @patch("src.postman_api.update_collections.requests.put")
    def test_puts_loaded_collection_to_its_uid_endpoint(
        self,
        mock_put: MagicMock,
        tmp_path: Path,
        sample_collection_response: CollectionResponse,
    ) -> None:
        # TODO: write sample_collection_response to a file, call update_collection(path)
        # TODO: assert mock_put was called with a url containing the collection's uid
        pass
