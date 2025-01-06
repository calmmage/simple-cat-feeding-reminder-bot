from datetime import datetime

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from botspot.components.bot_commands_menu import add_hidden_command
from botspot.utils import reply_safe
from botspot.utils.deps_getters import get_database

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
