from datetime import date, datetime, timedelta
from typing import List
import pandas as pd
from pandas.tseries.holiday import USFederalHolidayCalendar, Holiday, nearest_workday
from pandas import DateOffset

# US Stock Market Holidays (NYSE/NASDAQ)
class USMarketCalendar(USFederalHolidayCalendar):
    """US Stock Market Holiday Calendar"""
    
    rules = [
        Holiday('New Years Day', month=1, day=1, observance=nearest_workday),
        Holiday('Martin Luther King Jr. Day', month=1, day=1, offset=DateOffset(weekday=0, weeks=3)),
        Holiday('Presidents Day', month=2, day=1, offset=DateOffset(weekday=0, weeks=3)),
        Holiday('Good Friday', month=1, day=1, offset=[pd.Easter(), pd.DateOffset(days=-2)]),
        Holiday('Memorial Day', month=5, day=31, offset=DateOffset(weekday=0, weeks=-1)),
        Holiday('Juneteenth', month=6, day=19, observance=nearest_workday),
        Holiday('Independence Day', month=7, day=4, observance=nearest_workday),
        Holiday('Labor Day', month=9, day=1, offset=DateOffset(weekday=0, weeks=1)),
        Holiday('Thanksgiving', month=11, day=1, offset=DateOffset(weekday=3, weeks=4)),
        Holiday('Christmas', month=12, day=25, observance=nearest_workday),
    ]

def is_trading_day(check_date: date) -> bool:
    """
    Check if a given date is a US stock market trading day
    
    Args:
        check_date: Date to check
    
    Returns:
        True if market is open, False otherwise
    """
    # Check if weekend
    if check_date.weekday() >= 5:  # Saturday=5, Sunday=6
        return False
    
    # Check if holiday
    cal = USMarketCalendar()
    holidays = cal.holidays(start=check_date, end=check_date)
    
    return len(holidays) == 0

def get_last_trading_day(reference_date: date = None) -> date:
    """
    Get the most recent trading day (or current day if market is open)
    
    Args:
        reference_date: Date to check from (defaults to today)
    
    Returns:
        Last trading day
    """
    if reference_date is None:
        reference_date = datetime.now().date()
    
    current = reference_date
    
    # Go back until we find a trading day
    while not is_trading_day(current):
        current -= timedelta(days=1)
    
    return current

def get_trading_days_between(start_date: date, end_date: date) -> List[date]:
    """
    Get list of all trading days between two dates (inclusive)
    
    Args:
        start_date: Start date
        end_date: End date
    
    Returns:
        List of trading days
    """
    from pandas.tseries.offsets import CustomBusinessDay
    
    cal = USMarketCalendar()
    us_bd = CustomBusinessDay(calendar=cal)
    
    # Generate business days
    trading_days = pd.bdate_range(
        start=start_date,
        end=end_date,
        freq=us_bd
    )
    
    return [d.date() for d in trading_days]

def detect_missing_days(existing_dates: List[date], start_date: date, end_date: date) -> List[date]:
    """
    Detect missing trading days in a date range
    
    Args:
        existing_dates: List of dates we already have
        start_date: Expected start of range
        end_date: Expected end of range
    
    Returns:
        List of missing trading days
    """
    expected_days = set(get_trading_days_between(start_date, end_date))
    existing_days = set(existing_dates)
    
    missing = expected_days - existing_days
    
    return sorted(list(missing))

