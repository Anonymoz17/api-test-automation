import argparse
from argparse import ArgumentParser, Namespace, _SubParsersAction
from pathlib import Path

from src.postman_api.export_collections import (
    export_collections,
    resolve_and_fetch_collections,
)
from src.postman_api.update_collections import resolve_and_update_collections
from src.postman_api.workspace import get_all_collections, get_collection_uids
from src.schema import CollectionResponse


def _add_workspace_subcommand(subparsers: _SubParsersAction[ArgumentParser]) -> None:
    workspace_parser: ArgumentParser = subparsers.add_parser(
        name        = "workspace",
        help        = "Inspect the Postman workspace",
        description = "Inspect the Postman workspace configured via POSTMAN_PARKEE_WORKSPACE_UID",
    )
    workspace_subparsers: _SubParsersAction[ArgumentParser] = workspace_parser.add_subparsers(
        dest="workspace_command",
        required=True,
    )

    list_parser: ArgumentParser = workspace_subparsers.add_parser(
        "list",
        help="List all collection UIDs in the workspace",
    )
    list_parser.set_defaults(func=handle_workspace_list)


def _add_export_subcommand(subparsers: _SubParsersAction[ArgumentParser]) -> None:
    export_parser: ArgumentParser = subparsers.add_parser(
        name        = "export",
        help        ="Export one or more Postman collections to the exports/ directory",
        description ="Fetches collection(s) from the Postman API and writes them to disk as JSON",
    )
    target_group = export_parser.add_mutually_exclusive_group(required=True)
    _ = target_group.add_argument(
        "--uid",
        nargs="+",
        metavar="COLLECTION_UID",
        help="One or more collection UIDs to export",
    )
    _ = target_group.add_argument(
        "--all",
        action="store_true",
        help="Export every collection in the workspace",
    )
    export_parser.set_defaults(func=handle_export)


def _add_update_subcommand(subparsers: _SubParsersAction[ArgumentParser]) -> None:
    update_parser: ArgumentParser = subparsers.add_parser(
        name        = "update",
        help        = "Push local collection file(s) back to Postman",
        description = "Reads exported collection JSON file(s) and updates the matching Postman collection via its uid",
    )
    _ = update_parser.add_argument(
        "path",
        type    = Path,
        help    = "Path to a single collection .json file or a directory containing collection .json files",
    )
    update_parser.set_defaults(func=handle_update)


def _add_run_subcommand(subparsers: _SubParsersAction[ArgumentParser]) -> None:
    # Skeleton: intended to drive Newman runs against exported collections (see newman-runs/).
    run_parser: ArgumentParser = subparsers.add_parser(
        name        = "run",
        help        = "[not yet implemented] Run a collection with Newman",
        description = "Run a Postman collection via Newman and store the results in newman-runs/",
    )
    _ = run_parser.add_argument(
        "collection",
        type    = Path,
        help    = "Path to the collection .json file to run",
    )
    _ = run_parser.add_argument(
        "-e", 
        "--environment",
        type    = Path,
        default = None,
        help    = "Path to a Postman environment .json file",
    )
    run_parser.set_defaults(func=handle_run)


def handle_workspace_list(_args: Namespace) -> None:
    collections: CollectionResponse = get_all_collections()
    uids: list[str]                 = get_collection_uids(collections=collections)

    for collection, uid in zip(collections["collections"], uids):
        print(f"{uid}\t{collection['name']}")


def handle_export(args: Namespace) -> None:
    if args.all:
        collections: CollectionResponse = get_all_collections()
        uids: list[str]                 = get_collection_uids(collections=collections)
    else:
        uids                            = args.uid

    fetched_collections: list[CollectionResponse] = resolve_and_fetch_collections(collection_uids=uids)
    export_collections(fetched_collections=fetched_collections)


def handle_update(args: Namespace) -> None:
    _ = resolve_and_update_collections(collections_path=args.path)


def handle_run(_args: Namespace) -> None:
    raise NotImplementedError("The 'run' command (Newman integration) is not implemented yet.")


def build_parser() -> ArgumentParser:
    parser: ArgumentParser = argparse.ArgumentParser(
        prog        = "api-test-automation-tool",
        description = "Test APIs automated",
    )
    subparsers: _SubParsersAction[ArgumentParser] = parser.add_subparsers(
        dest        = "command",
        required    = True,
    )

    _add_workspace_subcommand(subparsers=subparsers)
    _add_export_subcommand(subparsers=subparsers)
    _add_update_subcommand(subparsers=subparsers)
    _add_run_subcommand(subparsers=subparsers)

    return parser


def main() -> None:
    parser: ArgumentParser = build_parser()
    args: Namespace = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
