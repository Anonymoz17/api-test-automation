import re
from datetime import datetime, timedelta, timezone


def get_datetime() -> str:
    """
    Returns the current GMT+7 local time formatted safely for filenames.
    Format: YYYY-MM-DDTHH-MM-SS
    """
    # 1. Get current time explicitly in GMT+7
    gmt_plus_7: timezone = timezone(offset=timedelta(hours=7))
    now_gmt7: datetime = datetime.now(tz=gmt_plus_7)
    
    # 2. Format using dashes instead of colons for file system safety
    # Note: %M is minutes, %S is seconds
    return now_gmt7.strftime(format="%Y%m%d_%H%M%S")


def sanitize(text: str) -> str:
    text = text.strip()
    cleaned_text: str = re.sub(r'[^a-zA-Z0-9 ]', '', text) 

    return cleaned_text
