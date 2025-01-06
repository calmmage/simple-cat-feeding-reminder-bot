import re
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Optional, Tuple
from zoneinfo import ZoneInfo

from loguru import logger


@lru_cache(maxsize=1)
def get_server_offset() -> timedelta:
    """Get the offset between server's local time and UTC (cached for 1 hour)"""
    now = datetime.now()
    now_utc = datetime.now(ZoneInfo("UTC")).replace(tzinfo=None)
    offset = now - now_utc
    logger.debug(
        f"Server timezone offset calculated:\n"
        f"Server time: {now}\n"
        f"UTC time: {now_utc}\n"
        f"Offset: {offset}"
    )
    return offset


def clear_server_offset_cache() -> None:
    """Clear the server offset cache (call this during DST changes)"""
    get_server_offset.cache_clear()


def parse_timezone_offset(timezone_str: str) -> Optional[Tuple[int, int]]:
    """
    Parse timezone string in format GMT±HH:MM or GMT±HH
    Returns tuple of (hours, minutes) or None if invalid
    """
    # Match patterns like GMT+5, GMT+05, GMT+5:30, GMT+05:30, GMT-5 etc.
    pattern = r"^GMT(?P<sign>[+-])(?P<hours>\d{1,2})(?::(?P<minutes>\d{2}))?$"
    match = re.match(pattern, timezone_str.upper().strip())

    if not match:
        logger.warning(f"Failed to parse timezone string: {timezone_str}")
        return None

    hours = int(match.group("hours"))
    minutes = int(match.group("minutes") or "0")
    sign = 1 if match.group("sign") == "+" else -1

    logger.debug(f"Parsed timezone {timezone_str} -> {sign * hours:+d}:{abs(minutes):02d}")
    return (sign * hours, sign * minutes)


def convert_time_to_gmt(hour: int, minute: int, timezone_str: str) -> Tuple[int, int]:
    """Convert hour:minute from given timezone to GMT hour:minute"""
    offset = parse_timezone_offset(timezone_str)
    if offset is None:
        logger.warning(f"Invalid timezone format: {timezone_str}, using original time")
        return hour, minute

    offset_hours, offset_minutes = offset
    # Convert to total minutes for easier calculation
    # Subtract both server offset and user's timezone offset
    total_minutes = (
        hour * 60
        + minute
        - (offset_hours * 60 + offset_minutes)  # User's timezone offset
        # - (server_hours * 60 + server_minutes)  # Server's timezone offset
    )

    # Handle day wrap-around
    while total_minutes < 0:
        total_minutes += 24 * 60
    total_minutes %= 24 * 60

    gmt_hour = total_minutes // 60
    gmt_minute = total_minutes % 60

    logger.debug(
        f"Converting {hour:02d}:{minute:02d} {timezone_str} to GMT:\n"
        f"User offset: {offset_hours:+d}:{abs(offset_minutes):02d}\n"
        # f"Server offset: {server_hours:+d}:{abs(server_minutes):02d}\n"
        f"Result: {gmt_hour:02d}:{gmt_minute:02d} GMT"
    )

    return gmt_hour, gmt_minute


def get_user_local_time(timezone_str: str) -> datetime:
    """Convert GMT time to user's local time for display purposes"""
    base_time = datetime.now(tz=ZoneInfo("UTC"))

    offset = parse_timezone_offset(timezone_str)
    if offset is None:
        logger.warning(f"Invalid timezone format: {timezone_str}, using original time")
        return base_time

    hours, minutes = offset

    # First convert from server time to user's timezone
    return base_time + timedelta(hours=hours, minutes=minutes)


def get_true_utc_time() -> datetime:
    """Get current UTC time (for display purposes only)"""
    server_offset = get_server_offset()
    ts = datetime.now() - server_offset
    ts = ts.replace(tzinfo=ZoneInfo("UTC"))
    return ts
