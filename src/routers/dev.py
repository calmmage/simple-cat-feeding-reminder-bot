from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from botspot.components.bot_commands_menu import add_hidden_command
from botspot.utils import reply_safe
from botspot.utils.deps_getters import get_database

from src.utils.timezone_utils import get_true_utc_time, get_user_local_time

router = Router()


@add_hidden_command("dbwrite", "Write test feeding record")
@router.message(Command("dbwrite"))
async def db_write(message: Message) -> None:
    """Write test feeding record to database"""
    db = get_database()
    await db.feedings.insert_one(
        {
            "user_id": message.from_user.id,
            "timestamp": datetime.now(),
            "schedule_type": "test",
            "photo_id": None,
        }
    )
    await reply_safe(message, "Test feeding record written to database!")


@add_hidden_command("dbread", "Read feeding records")
@router.message(Command("dbread"))
async def db_read(message: Message) -> None:
    """Read feeding records from database"""
    db = get_database()
    cursor = db.feedings.find({"user_id": message.from_user.id})
    items = await cursor.to_list(length=100)
    if not items:
        await reply_safe(message, "No feeding records found!")
        return

    text = "Your feeding records:\n\n"
    for item in items:
        text += f"Time: {item['timestamp'].strftime('%Y-%m-%d %H:%M')}\n"
        text += f"Schedule: {item['schedule_type']}\n"
        if item.get("photo_id"):
            text += "📸 With photo\n"
        text += "\n"

    await reply_safe(message, text)


@add_hidden_command("checktz", "Check timezone calculations")
@router.message(Command("checktz"))
async def check_timezone(message: Message) -> None:
    """Debug timezone calculations"""
    # Get user's timezone
    user = await db_manager.get_user(message.from_user.id)
    timezone = user.get("timezone") if user else None

    if not timezone:
        await reply_safe(message, "You haven't set your timezone yet. Use /timezone to set it.")
        return

    true_utc = get_true_utc_time()
    system_utc = datetime.now(ZoneInfo("UTC"))
    user_time = get_user_local_time(timezone, base_time=true_utc)

    debug_info = (
        "Timezone Debug Info:\n"
        f"Your timezone: {timezone}\n"
        f"True UTC: {true_utc}\n"
        f"System UTC: {system_utc}\n"
        f"System offset: {true_utc - system_utc}\n"
        f"Your local time: {user_time}\n"
        "\nTime Server Status:"
    )

    # Check each time server
    for url, parser in TIME_SERVERS:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                server_time = parser(response)
                debug_info += f"\n{url.split('://')[1].split('/')[0]}: {server_time}"
            else:
                debug_info += f"\n{url.split('://')[1].split('/')[0]}: Error {response.status_code}"
        except Exception as e:
            debug_info += f"\n{url.split('://')[1].split('/')[0]}: Failed ({str(e)})"

    await reply_safe(message, debug_info)
