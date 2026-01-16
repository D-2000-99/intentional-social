"""
Week calculation utilities for digest processing.
"""
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple


def get_week_bounds(date: Optional[datetime] = None) -> Tuple[datetime, datetime]:
    """
    Get the start (Sunday 00:00) and end (Saturday 23:59:59) of the week containing the given date.
    If no date is provided, uses current date.
    
    Week definition: Sunday → Saturday
    
    Args:
        date: Optional datetime to calculate week for (defaults to now)
    
    Returns:
        Tuple of (week_start, week_end) in UTC
    """
    if date is None:
        date = datetime.now(timezone.utc)
    
    date_only = date.replace(hour=0, minute=0, second=0, microsecond=0)
    days_since_sunday = (date_only.weekday() + 1) % 7
    week_start = date_only - timedelta(days=days_since_sunday)
    week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)
    
    return week_start, week_end

