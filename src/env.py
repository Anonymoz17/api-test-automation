import os
from pathlib import Path

from dotenv import load_dotenv

_ = load_dotenv()

PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent

GSHEETS_SERVICE_ACCOUNT: Path       = Path(PROJECT_ROOT / "sheets_service_account.json")
GSHEETS_SPREADSHEET_ID: str         = str(os.getenv("GSHEETS_SPREADSHEET_ID"))

POSTMAN_API_WORKSPACE_UID: str      = str(os.getenv("POSTMAN_PARKEE_WORKSPACE_UID"))
POSTMAN_API_BASE_URL: str           = str(os.getenv("POSTMAN_BASE_URL"))
POSTMAN_API_KEY: str                = str(os.getenv("POSTMAN_API_KEY"))
POSTMAN_API_HEADERS: dict[str, str] = {"X-Api-Key": POSTMAN_API_KEY}

