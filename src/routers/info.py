"""
Stats commands for the cat feeding bot
"""

import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from botspot.components.bot_commands_menu import Visibility, add_command
from botspot.utils import reply_safe

from src.database import DatabaseManager
from src.utils.timezone_utils import get_timezone_obj, get_user_local_time

router = Router()
db_manager = DatabaseManager()


@add_command("stats", "Show your feeding statistics")
@router.message(Command("stats"))
async def show_stats(message: Message) -> None:
    """Show basic feeding statistics for the current user"""
    assert message.from_user is not None

    # Get user's timezone
    user = await db_manager.get_user(message.from_user.id)

    timezone = user.get("timezone") if user else "UTC"

    now = get_user_local_time(timezone)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())

    feedings = await db_manager.get_user_feedings(message.from_user.id)

    utc = ZoneInfo("UTC")
    today_feedings = [f for f in feedings if f["timestamp"].replace(tzinfo=utc) >= today_start]
    week_feedings = [f for f in feedings if f["timestamp"].replace(tzinfo=utc) >= week_start]

    # Calculate stats
    stats_text = (
        "📊 <b>Your Feeding Stats</b>\n\n"
        f"Today: {len(today_feedings)} feedings\n"
        f"This week: {len(week_feedings)} feedings\n"
        f"Total: {len(feedings)} feedings\n\n"
        f"Photos shared: {sum(1 for f in feedings if f.get('photo_id'))}\n"
        f"Videos shared: {sum(1 for f in feedings if f.get('video_id'))}"
    )

    await reply_safe(message, stats_text)


@add_command("full_stats", "Show detailed feeding statistics")
@router.message(Command("full_stats"))
async def show_full_stats(message: Message) -> None:
    """Show detailed feeding statistics with history"""
    assert message.from_user is not None

    # Get user's timezone
    user = await db_manager.get_user(message.from_user.id)
    timezone = user.get("timezone") if user else "UTC"
    tz = get_timezone_obj(timezone)

    feedings = await db_manager.get_user_feedings(message.from_user.id)
    if not feedings:
        await reply_safe(message, "No feeding history found.")
        return

    # Sort feedings by timestamp
    feedings.sort(key=lambda x: x["timestamp"], reverse=True)

    # Generate detailed stats
    stats_text = "📊 <b>Detailed Feeding Statistics</b>\n\n"

    # Last 5 feedings
    stats_text += "<b>Recent Feedings:</b>\n"
    for feeding in feedings[:5]:
        timestamp = feeding["timestamp"].astimezone(tz)
        media = ""
        if feeding.get("photo_id"):
            media = " 📷"
        elif feeding.get("video_id"):
            media = " 🎥"
        stats_text += f"- {timestamp.strftime('%Y-%m-%d %H:%M')}{media}\n"

    utc = ZoneInfo("UTC")
    # Daily summary for the last 7 days
    stats_text += "\n<b>Daily Summary (Last 7 days):</b>\n"
    for i in range(7):
        date = datetime.now(tz) - timedelta(days=i)
        day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        day_feedings = [
            f for f in feedings if day_start <= f["timestamp"].replace(tzinfo=utc) < day_end
        ]

        day_name = "Today" if i == 0 else "Yesterday" if i == 1 else date.strftime("%A")
        stats_text += f"- {day_name}: {len(day_feedings)} feedings\n"

    # Schedule info
    user_schedule = await db_manager.get_user_schedule(message.from_user.id)
    if user_schedule:
        stats_text += f"\n<b>Current Schedule:</b> {user_schedule['type']}\n"
        if user_schedule.get("times"):
            stats_text += f"Times: {', '.join(user_schedule['times'])}\n"

    await reply_safe(message, stats_text)


@add_command("help", "Show available commands")
@router.message(Command("help"))
async def help_command(message: Message) -> None:
    """Show help message with available commands"""
    from botspot.components.bot_commands_menu import commands

    # Main commands section
    text = "🐱 <b>Cat Feeding Bot Commands</b>\n\n"
    text += "<b>Main Commands:</b>\n"
    for cmd, info in commands.items():
        if info.visibility == Visibility.PUBLIC:
            text += f"/{cmd} - {info.description}\n"

    assert message.from_user is not None

    # Add hidden commands section for admin
    # Get bot info to check if user is owner
    text += "\n<b>Hidden Commands:</b>\n"
    for cmd, info in commands.items():
        if info.visibility == Visibility.HIDDEN:
            text += f"/{cmd} - {info.description}\n"

        if message.from_user.id == int(os.getenv("ADMIN_USER_ID", 0)):
            if info.visibility == Visibility.ADMIN_ONLY:
                text += f"/{cmd} - {info.description}\n"

    await reply_safe(message, text)
