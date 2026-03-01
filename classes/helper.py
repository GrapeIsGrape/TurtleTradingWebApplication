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
    Check if NYSE market is currently open (in HK timezone).
    
    US market opens at 9:30 AM ET and closes at 4:00 PM ET.
    In HK timezone:
    - Standard Time (Nov-Mar): Opens 10:30 PM HKT, closes 5:00 AM HKT next day
    - Daylight Saving Time (Mar-Nov): Opens 9:30 PM HKT, closes 4:00 AM HKT next day
    
    Returns:
        True if US market is currently open (comparing in HK timezone)
    """
    import pytz
    
    today_date = str(date.today())
    
    nyse = pmc.get_calendar('NYSE')
    schedule = nyse.schedule(start_date=today_date, end_date=today_date)
    
    # If market is closed today (weekends, holidays)
    if len(schedule) == 0:
        return False
    
    # Get market open and close times - they come with timezone info
    market_open_et = schedule['market_open'].iloc[0].to_pydatetime()
    market_close_et = schedule['market_close'].iloc[0].to_pydatetime()
    
    # Convert to HK timezone
    hk_tz = pytz.timezone('Asia/Hong_Kong')
    market_open_hk = market_open_et.astimezone(hk_tz)
    market_close_hk = market_close_et.astimezone(hk_tz)
    
    # Get current time in HK timezone
    current_time_hk = datetime.now(hk_tz)
    
    # Handle case where market close is on the next day (common for HK timezone)
    if market_close_hk < market_open_hk:
        # Market spans across midnight
        return current_time_hk >= market_open_hk or current_time_hk <= market_close_hk
    else:
        return market_open_hk <= current_time_hk <= market_close_hk
