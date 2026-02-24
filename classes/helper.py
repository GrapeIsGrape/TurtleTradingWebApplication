from datetime import date, datetime
import pandas_market_calendars as pmc
import pandas as pd

def get_duplicated_items_from_lists(multiple_lists):
    combined_list = []
    for single_list in multiple_lists:
        combined_list += single_list

    duplicates = set()
    seen = set()
    for item in combined_list:
        if item in seen:
            duplicates.add(item)
        else:
            seen.add(item)

    return duplicates

def check_if_market_is_open():
    market_is_open = False
    today_date = str(date.today())
    hk_timezone = 'Asia/Hong_Kong'
    nyse = pmc.get_calendar('NYSE')
    schedule = nyse.schedule(start_date=today_date, end_date=today_date)
    if len(schedule['market_open']) > 0:
        local_open = schedule['market_open'].dt.tz_convert(hk_timezone)[0].to_pydatetime()
        local_close = schedule['market_close'].dt.tz_convert(hk_timezone)[0].to_pydatetime()
        current_time = datetime.now()
        print(type(local_open), type(local_close), type(current_time))
        if local_open <= current_time and current_time <= local_close:
            market_is_open = True
    return market_is_open