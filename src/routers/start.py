from aiogram import Router, html
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from botspot.components.bot_commands_menu import add_command
from botspot.utils import answer_safe, reply_safe

from src.routers.common import db_manager
from src.routers.schedule import clear_user_schedule, setup_schedule
from src.routers.settings import setup_timezone

router = Router()


@add_command("start", "Start the bot")
@router.message(CommandStart())
async def command_start_handler(message: Message, state: FSMContext) -> None:
    """Send a welcome message when the command /start is issued"""
    # Create or update user in database
    user = await db_manager.create_or_update_user(message)

    assert message.from_user is not None

    # Welcome message
    await answer_safe(
        message,
        f"Hello, {html.bold(message.from_user.full_name)}!\n\n"
        "This is a cat feeding reminder bot.\n"
        "Use /help to see available commands.",
    )

    # If new user (no timezone set), ask for timezone
    if not user.get("timezone"):
        await reply_safe(
            message,
            "I notice you haven't set your timezone yet. "
            "This is important for scheduling reminders correctly.",
        )
        await setup_timezone(message)

    await setup_schedule(message, state)


@add_command("stop", "Stop all reminders")
@router.message(Command("stop"))
async def stop_command(message: Message) -> None:
    """Stop all reminders for the user"""
    clear_user_schedule(message.chat.id)

    assert message.from_user is not None
    # Update user's schedule in database
    await db_manager.save_user_schedule(message.from_user.id, "stopped", [])

    await reply_safe(
        message,
        "All reminders have been stopped. Use /setup to create a new schedule.",
    )
