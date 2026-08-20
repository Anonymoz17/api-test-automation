from typing import Required, TypeAlias, TypedDict

JSON: TypeAlias = (
    None
    | bool
    | int
    | float
    | str
    | list["JSON"]
    | dict[str, "JSON"]
)

class CollectionInfo(TypedDict):
    name: str
    uid: str

class CollectionData(TypedDict):
    info: CollectionInfo
    name: str
    uid: str

class CollectionResponse(TypedDict):
    collection: CollectionData
    collections: list[CollectionData]

# === 
# Newman CLI Config

class GSheetsConfig(TypedDict):
    spreadsheet_id: str
    worksheet_id: str
    handler: str

class ReporterConfig(TypedDict, total=False):
    json: bool
    progress: bool

class NewmanConfig(TypedDict, total=False):
    collection: Required[str]
    environment: str
    gsheets: GSheetsConfig
    reporter: ReporterConfig
    tests: str
