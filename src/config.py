import os
from pathlib import Path

from dotenv import load_dotenv

_ = load_dotenv()

PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent

POSTMAN_API_WORKSPACE_UID: str      = str(os.getenv("POSTMAN_PARKEE_WORKSPACE_UID"))
POSTMAN_API_BASE_URL: str           = str(os.getenv("POSTMAN_BASE_URL"))
POSTMAN_API_KEY: str                = str(os.getenv("POSTMAN_API_KEY"))
POSTMAN_API_HEADERS: dict[str, str] = {"X-Api-Key": POSTMAN_API_KEY}

