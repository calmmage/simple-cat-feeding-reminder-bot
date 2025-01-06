from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from botspot import ask_user
from botspot.components.bot_commands_menu import add_command
from botspot.utils import reply_safe
from loguru import logger

from src.routers.common import db_manager
from src.utils import create_state
from src.utils.timezone_utils import get_user_local_time, parse_timezone_offset

router = Router()


@add_command("timezone", "Set your timezone")
@router.message(Command("timezone"))
async def timezone_setup(message: Message, state: FSMContext) -> None:
    """Setup user timezone"""
    await setup_timezone(message)


async def setup_timezone(message: Message, timezone_str=None) -> None:
    """Ask user for timezone and save it"""
    state = create_state(message.chat.id)

    while True:
        if timezone_str is None:
            response = await ask_user(
                chat_id=message.chat.id,
                question=(
                    "Please enter your timezone in GMT±HH:MM format\n"
                    "Examples: GMT+3, GMT+03:00, GMT-5:30\n"
                    "Type 'cancel' to cancel"
                ),
                state=state,
                timeout=300.0,
            )

            if not response or response.lower() == "cancel":
                await reply_safe(message, "Timezone setup cancelled.")
                return

            timezone_str = response.strip()
        timezone_offset = parse_timezone_offset(timezone_str)

        if timezone_offset is None:
            await reply_safe(
                message,
                "Invalid timezone format. Please use GMT±HH:MM format.\n"
                "Examples: GMT+3, GMT+03:00, GMT-5:30",
            )
            continue

        hours, minutes = timezone_offset
        formatted_timezone = f"GMT{'+' if hours >= 0 else ''}{hours:02d}:{abs(minutes):02d}"

        # Save to database
        assert message.from_user is not None
        await db_manager.update_user_timezone(message.from_user.id, formatted_timezone)

        # Get current time in user's timezone
        user_time = get_user_local_time(formatted_timezone)
        system_utc = datetime.now(tz=ZoneInfo("UTC"))

        logger.debug(
            "Timezone setup:\n"
            f"System UTC time: {system_utc}\n"
            f"User timezone: {formatted_timezone}\n"
            f"Calculated user time: {user_time}\n"
        )

        await reply_safe(
            message,
            f"Timezone set to {formatted_timezone}\n"
            f"Your current time should be around {user_time.strftime('%H:%M')}",
        )
        return
