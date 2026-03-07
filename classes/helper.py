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
    from datetime import timedelta

    now_utc = datetime.now(timezone.utc)

    nyse = pmc.get_calendar('NYSE')
    start_date = (now_utc.date() - timedelta(days=1)).isoformat()
    end_date = (now_utc.date() + timedelta(days=1)).isoformat()
    schedule = nyse.schedule(start_date=start_date, end_date=end_date)

    if schedule.empty:
        return False

    for _, row in schedule.iterrows():
        market_open_utc = row['market_open'].to_pydatetime()
        market_close_utc = row['market_close'].to_pydatetime()
        if market_open_utc <= now_utc <= market_close_utc:
            return True

    return False


def check_if_previous_night_market_was_open() -> bool:
    """
    Check if a NYSE session closed within the past 24 hours (UTC).

    This is timezone-safe: it does not rely on the current ET calendar date,
    which can roll past midnight before HKT does, causing false negatives when
    the script runs in the afternoon/evening HKT.

    Returns:
        True if a NYSE closing bell occurred within the last 24 hours
    """
    from datetime import timedelta

    now_utc = datetime.now(timezone.utc)
    window_start = now_utc - timedelta(hours=24)

    nyse = pmc.get_calendar('NYSE')
    schedule = nyse.schedule(
        start_date=window_start.date().isoformat(),
        end_date=now_utc.date().isoformat(),
    )

    if schedule.empty:
        return False

    for _, row in schedule.iterrows():
        market_close_utc = row['market_close'].to_pydatetime()
        if window_start <= market_close_utc <= now_utc:
            return True

    return False
