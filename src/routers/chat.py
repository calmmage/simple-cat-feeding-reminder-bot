from aiogram import F, Router
from aiogram.types import Message
from botspot.utils import reply_safe

from src.database import DatabaseManager
from src.routers.settings import setup_timezone

router = Router()

# plan: dev/todo.md

SCHEDULES = {
    "2 times": ["08:00", "20:00"],
    "3 times": ["08:00", "14:00", "20:00"],
    "4 times": ["08:00", "12:00", "16:00", "20:00"],
    "Manual": None,  # Not implemented yet
}

db_manager = DatabaseManager()


@router.message(F.chat.type == "private")
async def handle_messages(message: Message) -> None:
    """Handle non-command messages"""
    # if message.chat.type == "private":
    # fallback 1: if message text looks like timezone - setup timezone using it
    if message.text and "gmt" in message.text.lower():
        return await setup_timezone(message, message.text)

    return await reply_safe(
        message,
        "This bot doesn't support casual chatting!\n\n"
        "Available commands:\n"
        "/start - Start the bot\n"
        "/setup - Setup feeding schedule\n"
        "/timezone - Set your timezone\n"
        "/fed - Register a feeding\n"
        "/stats - Show stats\n"
        "/full_stats - Show full stats\n"
        "/help - Show all commands",
    )
