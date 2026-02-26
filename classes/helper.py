"""Helper utilities for market operations and list manipulation."""

from datetime import date, datetime, timezone
from typing import List, Set, TypeVar
import pandas_market_calendars as pmc


T = TypeVar('T')


def get_duplicated_items_from_lists(multiple_lists: List[List[T]]) -> Set[T]:
    """
    Find items that appear in multiple lists.
    
    Args:
        multiple_lists: List of lists to check for duplicates across
        
    Returns:
        Set of items that appear in more than one list
    """
    combined_list = [item for single_list in multiple_lists for item in single_list]
    
    duplicates = set()
    seen = set()
    
    for item in combined_list:
        if item in seen:
            duplicates.add(item)
        else:
            seen.add(item)
    
    return duplicates


def check_if_market_is_open() -> bool:
    """
    Check if NYSE market is currently open.
    
    Returns:
        True if market is currently open (US market hours in HK timezone)
    """
    today_date = str(date.today())
    hk_timezone = 'Asia/Hong_Kong'
    
    nyse = pmc.get_calendar('NYSE')
    schedule = nyse.schedule(start_date=today_date, end_date=today_date)
    
    if len(schedule['market_open']) == 0:
        return False
    
    local_open = schedule['market_open'].dt.tz_convert(hk_timezone).iloc[0].to_pydatetime()
    local_close = schedule['market_close'].dt.tz_convert(hk_timezone).iloc[0].to_pydatetime()
    current_time = datetime.now(timezone.utc).astimezone()
    
    return local_open <= current_time <= local_close
