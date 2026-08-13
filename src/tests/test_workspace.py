from unittest.mock import MagicMock, patch

from src.schema import CollectionResponse

# from src.postman_api.workspace import get_all_collections, get_collection_uids


class TestGetAllCollections:
    @patch("src.postman_api.workspace.requests.get")
    def test_returns_parsed_response(
        self,
        mock_get: MagicMock,
        sample_collection_response: CollectionResponse,
    ) -> None:
        # TODO: mock_get.return_value.json.return_value = sample_collection_response
        # TODO: result = get_all_collections()
        # TODO: assert result == sample_collection_response
        pass

    @patch("src.postman_api.workspace.requests.get")
    def test_requests_scoped_to_configured_workspace(self, mock_get: MagicMock) -> None:
        # TODO: call get_all_collections() and assert mock_get was called with
        #       params={"workspace": {POSTMAN_API_WORKSPACE_UID}}
        pass


class TestGetCollectionUids:
    def test_excludes_the_postman_api_collection(self) -> None:
        # TODO: build a CollectionResponse containing a collection named "Postman API"
        #       plus at least one other, assert its uid is excluded from the result
        pass

    def test_returns_uid_for_each_remaining_collection(
        self,
        sample_collection_response: CollectionResponse,
    ) -> None:
        # TODO: assert get_collection_uids(sample_collection_response) == [...]
        pass
