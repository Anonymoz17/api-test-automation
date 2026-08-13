import gspread
from gspread import Client, Spreadsheet, Worksheet

from src.config import GSHEETS_SERVICE_ACCOUNT, GSHEETS_SPREADSHEET_ID

service_account: Client     = gspread.service_account(filename=GSHEETS_SERVICE_ACCOUNT)
spreadsheet_id: Spreadsheet = service_account.open_by_key(key=GSHEETS_SPREADSHEET_ID)

worksheet_1: Worksheet      = spreadsheet_id.sheet1


rows: list[list[str]] = worksheet_1.get(range_name="A1:K5")


def main():
    for row in rows:
        print(row)


if __name__ == "__main__":
    main()

