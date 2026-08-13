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

class ReporterConfig(TypedDict, total=False):
    json: str
    progress: bool

class NewmanConfig(TypedDict, total=False):
    collection: Required[str]
    environment: str
    reporter: ReporterConfig

