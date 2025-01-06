import re
from datetime import datetime, timedelta
from distutils.util import strtobool
from functools import lru_cache
from os import getenv
from pathlib import Path
from typing import Optional, Tuple
from zoneinfo import ZoneInfo

import requests
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from loguru import logger


def parse_timezone_offset(timezone_str: str) -> Optional[Tuple[int, int]]:
    """
    Parse timezone string in format GMT±HH:MM or GMT±HH
    Returns tuple of (hours, minutes) or None if invalid
    """
    # Match patterns like GMT+5, GMT+05, GMT+5:30, GMT+05:30, GMT-5 etc.
    pattern = r"^GMT(?P<sign>[+-])(?P<hours>\d{1,2})(?::(?P<minutes>\d{2}))?$"
    match = re.match(pattern, timezone_str.upper().strip())

    if not match:
        return None

    hours = int(match.group("hours"))
    minutes = int(match.group("minutes") or "0")
    sign = 1 if match.group("sign") == "+" else -1

    # Validate hours and minutes
    if hours > 14 or minutes >= 60:  # UTC-12 to UTC+14 are valid
        return None

    return (sign * hours, sign * minutes)


def get_server_timezone() -> str:
    """Get server timezone in GMT±HH:MM format"""
    # Check for environment variable override
    env_timezone = getenv("SERVER_TIMEZONE")
    if env_timezone and parse_timezone_offset(env_timezone):
        return env_timezone.upper()

    try:
        # Get local timezone name
        local_tz = datetime.now().astimezone().tzinfo

        # Convert current time to UTC
        now_local = datetime.now(local_tz)
        now_utc = now_local.astimezone(ZoneInfo("UTC"))

        # Calculate offset
        offset = now_local.utcoffset()
        if offset is None:
            logger.warning("Could not determine server timezone offset, falling back to UTC")
            return "GMT+00:00"

        hours = int(offset.total_seconds() // 3600)
        minutes = int((offset.total_seconds() % 3600) // 60)

        return f"GMT{'+' if hours >= 0 else ''}{hours:02d}:{abs(minutes):02d}"
    except Exception as e:
        logger.warning(f"Error determining server timezone: {e}, falling back to UTC")
        return "GMT+00:00"


TIME_SERVERS = [
    (
        "http://worldtimeapi.org/api/timezone/UTC",
        lambda r: datetime.fromisoformat(r.json()["datetime"].replace("Z", "+00:00")),
    ),
    (
        "https://www.time.gov/actualtime.cgi",
        lambda r: datetime.fromtimestamp(int(r.text.split('"')[1]) / 1000.0, ZoneInfo("UTC")),
    ),
    (
        "http://showcase.api.linx.twenty57.net/UnixTime/ticks",
        lambda r: datetime.fromtimestamp(
            int(r.json()["Ticks"]) / 10000000 - 62135596800, ZoneInfo("UTC")
        ),
    ),
]


def get_true_utc_time() -> datetime:
    """Get accurate UTC time from internet time servers"""
    if strtobool(getenv("DISABLE_INTERNET_TIME", "false")):
        system_time = datetime.now(ZoneInfo("UTC"))
        logger.debug(f"Internet time disabled, using system time: {system_time}")
        return system_time

    for url, parser in TIME_SERVERS:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                true_time = parser(response)
                system_time = datetime.now(ZoneInfo("UTC"))
                offset = true_time - system_time
                logger.debug(
                    f"Time from {url}:"
                    f"\nTrue time: {true_time}"
                    f"\nSystem time: {system_time}"
                    f"\nOffset: {offset}"
                )
                return true_time
        except Exception as e:
            logger.debug(f"Failed to get time from {url}: {e}")
            continue

    logger.warning("All time servers failed, falling back to system time")
    return datetime.now(ZoneInfo("UTC"))


def get_user_local_time(timezone_str: str, base_time: Optional[datetime] = None) -> datetime:
    """Convert UTC time to user's local time"""
    if base_time is None:
        base_time = get_true_utc_time()

    offset = parse_timezone_offset(timezone_str)
    if offset is None:
        logger.warning(f"Invalid timezone format: {timezone_str}, using UTC")
        return base_time

    hours, minutes = offset
    local_time = base_time + timedelta(hours=hours, minutes=minutes)

    logger.debug(
        f"Converting to local time:"
        f"\nBase UTC time: {base_time}"
        f"\nTimezone: {timezone_str}"
        f"\nOffset: {hours:+d}:{abs(minutes):02d}"
        f"\nLocal time: {local_time}"
    )

    return local_time


def get_utc_time(local_time: datetime, timezone_str: str) -> datetime:
    """Convert user's local time to UTC using true UTC time as reference"""
    offset = parse_timezone_offset(timezone_str)
    if offset is None:
        logger.warning(f"Invalid timezone format: {timezone_str}, using UTC")
        return local_time

    # Get current true UTC time for reference
    true_utc = get_true_utc_time()
    system_utc = datetime.now(ZoneInfo("UTC"))

    # Calculate system clock offset from true UTC
    system_offset = true_utc - system_utc

    hours, minutes = offset
    utc_time = local_time - timedelta(hours=hours, minutes=minutes) + system_offset

    logger.debug(
        f"Converting to UTC:"
        f"\nLocal time: {local_time}"
        f"\nTimezone: {timezone_str}"
        f"\nOffset: {hours:+d}:{abs(minutes):02d}"
        f"\nSystem offset: {system_offset}"
        f"\nUTC time: {utc_time}"
    )

    return utc_time


def get_current_utc_time() -> datetime:
    """Get current UTC time, using cached offset from true time"""
    true_utc, system_utc = _cached_true_utc_time()

    # If cache is too old, refresh it
    if (datetime.now(ZoneInfo("UTC")) - system_utc) > timedelta(seconds=UTC_CACHE_DURATION):
        _cached_true_utc_time.cache_clear()
        true_utc, system_utc = _cached_true_utc_time()

    # Calculate current true time using cached offset
    system_offset = true_utc - system_utc
    return datetime.now(ZoneInfo("UTC")) + system_offset


@lru_cache(maxsize=1)
def _cached_true_utc_time() -> tuple[datetime, datetime]:
    """Get and cache true UTC time along with system time"""
    true_utc = get_true_utc_time()
    system_utc = datetime.now(ZoneInfo("UTC"))
    return true_utc, system_utc
