import json
from importlib import import_module
from pathlib import Path
from types import ModuleType
from typing import cast

import gspread
from gspread import Client, Spreadsheet, Worksheet

from src.env import GSHEETS_SERVICE_ACCOUNT
from src.schema import JSON, GSheetsConfig, NewmanConfig


def load_config_file(config_file: Path) -> NewmanConfig:
    with open(file=config_file, mode="r", encoding="utf-8") as f:
        return cast(NewmanConfig, json.load(fp=f))


def gsheets_orchestrator(newman_run_report: JSON, gsheets: GSheetsConfig) -> None:
    """
    Loads the handler module named in gsheets["handler"] and calls its
    update(report, spreadsheet_id, worksheet). The handler owns
    authentication (gspread.service_account) and whatever Sheets operations
    that specific test run needs — this function only dispatches to it.
    """

    spreadsheet_id: str         = gsheets.get("spreadsheet_id")
    worksheet_id: str           = gsheets.get("worksheet_id")
    
    gc: Client                  = gspread.service_account(filename=GSHEETS_SERVICE_ACCOUNT)

    spreadsheet: Spreadsheet    = gc.open_by_key(key=spreadsheet_id)
    worksheet: Worksheet        = spreadsheet.get_worksheet_by_id(id=worksheet_id)

    handler_path: str           = gsheets.get("handler")
    handler: ModuleType         = import_module(name=handler_path)
    handler.update(newman_run_report=newman_run_report, spreadsheet=spreadsheet, worksheet=worksheet)


def main():
    pass

if __name__ == "__main__":
    main()
