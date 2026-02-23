from .constants import *

#region True Range

def calculate_true_range_column(df):
    true_ranges = []
    for index, row in df.iterrows():
        true_ranges.append(calculate_true_range_at_index(df, index))
    df[TRUE_RANGE] = true_ranges
    return df

def calculate_true_range_at_index(df, index):
    row = df.loc[index]
    if index == 0 or len(df) == 1:
        true_range = round(row[HIGH] - row[LOW], ROUND_DP)
    else:
        previous_row = df.loc[index-1]

        today_high = float(row[HIGH])
        today_low = float(row[LOW])
        yersterday_close = float(previous_row[CLOSE])

        today_high_today_low_differrence = today_high - today_low
        today_high_yesterday_close_difference = abs(today_high - yersterday_close)
        today_low_yesterday_close_difference = abs(today_low - yersterday_close)

        true_range = round(max([today_high_today_low_differrence, today_high_yesterday_close_difference, today_low_yesterday_close_difference]), ROUND_DP)
            
    return true_range

#endregion

#region Average True Range

def calculate_average_true_range_column(df, days):
    average_true_ranges = []
    i = 0
    while i < len(df):
        if i > days:
            previous_average_true_range = average_true_ranges[-1]
            current_true_range = df.loc[i][TRUE_RANGE]
            atr = calculate_average_true_range(previous_average_true_range, current_true_range, days)
        else:
            atr = round(sum(df.loc[0:i][TRUE_RANGE]) / (i + 1), ROUND_DP)
        average_true_ranges.append(atr)
        i += 1

    df['ATR-' + str(days)] = average_true_ranges
    return df

def calculate_average_true_range(previous_average_true_range, current_true_range, days):
    return round((previous_average_true_range * (days - 1) + current_true_range) / days, ROUND_DP)

#endregion

#region Moving Average

def calculate_moving_average_column(df, days):
    if len(df) <= days:
        days = len(df)-1

    moving_averages = [] 
    for index, row in df.iterrows():
        if days > index:
            closes = df[CLOSE].loc[0:index]
            moving_average = round(sum(closes)/len(closes), ROUND_DP)
        else:
            moving_average = calculate_moving_average_at_index(df, index, days)
        moving_averages.append(moving_average)

    df['MA-' + str(days)] = moving_averages
    return df

def calculate_moving_average_at_index(df, index, days):
    if len(df) <= days:
        days = len(df)-1
        index = days-1
    
    closes = df[CLOSE].loc[index - days + 1:index]
    return round(sum(closes)/len(closes), ROUND_DP)

#endregion

#region N Days High

def calculate_n_days_high_column(df, n):
    if len(df) < n:
        n = len(df)

    n_days_highs = []
    for index, row in df.iterrows():
        if n >= index:
            n_days_high = max(df[HIGH].loc[0:index])
        else:
            n_days_high = calculate_n_days_high_at_index(df, index, n)
        n_days_highs.append(round(n_days_high, ROUND_DP))
    
    df[str(n) + '-Days High'] = n_days_highs
    return df

def calculate_n_days_high_at_index(df, index, n):
    if len(df) < n:
        n = len(df)
        index = n-1
    
    n_days_highs = df[HIGH].loc[index - n + 1:index]
    return round(max(n_days_highs), ROUND_DP)

#endregion

#region Days Low

def calculate_n_days_low_column(df, n):
    if len(df) < n:
        n = len(df)

    n_days_lows = []
    for index, row in df.iterrows():
        if n >= index:
            n_days_low = max(df[LOW].loc[0:index])
        else:
            n_days_low = calculate_n_days_low_at_index(df, index, n)
        n_days_lows.append(round(n_days_low, ROUND_DP))
    
    df[str(n) + '-Days Low'] = n_days_lows
    return df

def calculate_n_days_low_at_index(df, index, n):
    if len(df) < n:
        n = len(df)
        index = n-1
    
    n_days_lows = df[LOW].loc[index - n + 1:index]
    return round(max(n_days_lows), ROUND_DP)

#endregion

