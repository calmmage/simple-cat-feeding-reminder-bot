import json
import os
import random
from datetime import datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from aiogram import F, Router, html
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from botspot.components.ask_user_handler import ask_user, ask_user_choice, ask_user_raw
from botspot.components.bot_commands_menu import Visibility, add_command
from botspot.utils import answer_safe, reply_safe, send_safe
from botspot.utils.deps_getters import get_scheduler
from loguru import logger

from src.database import DatabaseManager
from src.utils import create_state, repo_root
from src.utils.timezone_utils import convert_time_to_gmt, get_user_local_time, parse_timezone_offset

router = Router()

# plan: dev/todo.md

SCHEDULES = {
    "2 times": ["08:00", "20:00"],
    "3 times": ["08:00", "14:00", "20:00"],
    "4 times": ["08:00", "12:00", "16:00", "20:00"],
    "Manual": None,  # Not implemented yet
}

db_manager = DatabaseManager()


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


@add_command("setup", "Setup feeding schedule")
@router.message(Command("setup"))
async def setup_schedule(message: Message, state: FSMContext) -> None:
    """Setup feeding schedule"""
    choices = {k: f"{k} - {v}" for k, v in SCHEDULES.items()}
    choices["Cancel"] = "Cancel"
    choice = await ask_user_choice(message.chat.id, "Pick a schedule", choices, state, timeout=None)

    if choice is None or choice == "Cancel":
        return

    if choice == "Manual":
        await reply_safe(message, "Manual schedule setup is not implemented yet.")
        return

    schedule = SCHEDULES[choice]
    assert message.from_user is not None

    # Save schedule to database
    await db_manager.save_user_schedule(message.from_user.id, choice, schedule)

    # Get user's timezone
    user = await db_manager.get_user(message.from_user.id)
    timezone = user.get("timezone") if user else None

    # Log schedule setup
    logger.debug(
        f"Setting up schedule:\n"
        f"User: {message.from_user.id}\n"
        f"Schedule type: {choice}\n"
        f"Times (local): {', '.join(schedule)}\n"
        f"Timezone: {timezone or 'UTC'}"
    )

    # Clear existing jobs
    clear_user_schedule(message.chat.id)

    # Add new jobs
    local_times = []
    for time in schedule:
        hour, minute = map(int, time.split(":"))
        local_times.append(f"{hour:02d}:{minute:02d}")

        # No need to convert time - let the scheduler handle it
        await schedule_reminder(
            chat_id=message.chat.id,
            hour=hour,  # Pass local time
            minute=minute,
            reschedule_if_missed=True,
            timezone=timezone,
        )

    # Log the final schedule
    logger.debug(
        f"Schedule setup complete:\n"
        f"User: {message.from_user.id}\n"
        f"Schedule type: {choice}\n"
        f"Local times: {', '.join(local_times)}\n"
        f"Timezone: {timezone or 'UTC'}"
    )

    # Show schedule to user
    await reply_safe(
        message,
        f"Scheduled to feed your cat {choice} times per day"
        f"{f' (in your timezone {timezone})' if timezone else ''}:\n"
        f"{', '.join(local_times)}"
        f"{'' if timezone else '\n\nNote: Times are in UTC. Use /timezone to set your timezone.'}",
    )

    # Send a test reminder right away
    await reply_safe(message, "Here's how the reminders will look:")
    await send_reminder(message.chat.id, reschedule_if_missed=False, log_reminder=False)


def clear_user_schedule(chat_id: int) -> None:
    """Clear all scheduled reminders for a user"""
    scheduler = get_scheduler()
    for job in scheduler.get_jobs():
        if job.id.startswith(f"feed_{chat_id}"):
            scheduler.remove_job(job.id)


async def schedule_reminder(
    chat_id: int,
    timestamp: Optional[datetime] = None,
    *,
    hour: Optional[int] = None,
    minute: Optional[int] = None,
    reschedule_if_missed: bool = True,
    timezone: Optional[str] = None,
) -> None:
    """Schedule a reminder"""
    scheduler = get_scheduler()

    if timestamp is not None:  # One-time reminder
        logger.debug(
            f"Scheduling one-time reminder:\n"
            f"GMT time: {timestamp}\n"
            f"Time until reminder: {timestamp - datetime.now()}"
        )

        job_id = f"followup_{chat_id}_{timestamp.strftime('%Y%m%d_%H%M')}"
        scheduler.add_job(
            send_reminder,
            "date",
            run_date=timestamp,
            id=job_id,
            args=[chat_id],
            kwargs={"reschedule_if_missed": reschedule_if_missed},
        )
    elif hour is not None and minute is not None:  # Recurring reminder
        if not timezone:
            raise ValueError("Timezone is required for recurring reminders")

        # Convert to GMT hours
        gmt_hour, gmt_minute = convert_time_to_gmt(hour, minute, timezone)

        logger.debug(
            f"Scheduling recurring reminder:\n"
            f"Local time: {hour:02d}:{minute:02d}\n"
            f"User timezone: {timezone}\n"
            f"GMT time: {gmt_hour:02d}:{gmt_minute:02d}"
        )

        job_id = f"feed_{chat_id}_{hour:02d}:{minute:02d}"
        scheduler.add_job(
            send_reminder,
            "cron",
            hour=gmt_hour,
            minute=gmt_minute,
            id=job_id,
            args=[chat_id],
            kwargs={"reschedule_if_missed": reschedule_if_missed},
        )
    else:
        raise ValueError("Either timestamp or hour and minute must be provided")


async def send_reminder(
    chat_id: int, reschedule_if_missed: bool = True, log_reminder: bool = True
) -> None:
    """Send feeding reminder"""
    # Get user's timezone for logging
    user = await db_manager.get_user(chat_id)
    timezone = user.get("timezone") if user else None

    now = datetime.now(ZoneInfo("UTC"))
    if timezone:
        local_time = get_user_local_time(timezone)
        logger.debug(
            f"Sending reminder:"
            f"\nUser: {chat_id}"
            f"\nUTC time: {now}"
            f"\nUser timezone: {timezone}"
            f"\nUser local time: {local_time}"
        )
    else:
        logger.debug(f"Sending reminder (no timezone):" f"\nUser: {chat_id}" f"\nUTC time: {now}")

    # todo: cancel if recently fed (And notify the user)
    # todo: provide both 'ask user' and 'choice' here (button to click + respond by message)
    # await send_safe(
    #     chat_id,
    #     "🐱 Time to feed your cat!\n"
    #     "Use /fed when done."
    # )

    # step 1: ask user something like 'did you feed your cat?'
    # step 2: if yes -> congratulate with random response from responses.json
    # step 2.a if with photo
    # step 2.b if without photo
    # step 3: if no (timeout) -> remind in 1 hour?
    # bonus: track last fed time (per user) and if recently - cancel the next reminder

    # step 1: ask user something like 'did you feed your cat?'
    state = create_state(chat_id)
    response = await ask_user_raw(
        chat_id=chat_id,
        question="Time to feed your cat! Did you?",
        state=state,
        timeout=300.0,
    )

    if response is not None:
        await register_meal(response, log_reminder=log_reminder)
    else:
        reply_text = "Time's up!"
        if reschedule_if_missed:
            reply_text += " Will remind again in 1 hour."
            await schedule_reminder(chat_id, timestamp=datetime.now() + timedelta(hours=1))
        await send_safe(chat_id, reply_text)


@add_command("fed", "Register a feeding")
@router.message(Command("fed"))
async def register_meal(message: Message, log_reminder: bool = True) -> None:
    """Register a feeding"""
    # Get user's current schedule
    assert message.from_user is not None
    user_schedule = await db_manager.get_user_schedule(message.from_user.id)
    schedule_type = user_schedule["type"] if user_schedule else "manual"

    # Todo: check for 'yes' or 'no' in the response using gpt
    # Todo: add a button or command. Command should be /fed. good for now

    # Get response message
    responses_path = repo_root / "src" / "resources" / "responses.json"
    with open(responses_path, encoding="utf-8") as file:
        responses = json.load(file)

    reply_text = random.choice(responses["feed_success"])

    if not (message.photo or message.video):
        reply_text += "\nNo photo though? :("
        # todo: request, not just ask

    # Log the feeding - save timestamp
    photo_id = message.photo[-1].file_id if message.photo else None
    video_id = message.video.file_id if message.video else None
    if log_reminder:
        feeding = await db_manager.log_feeding(
            user_id=message.from_user.id,
            schedule_type=schedule_type,
            photo_id=photo_id,
            video_id=video_id,
        )

    await reply_safe(message, reply_text)
    # bonus: track last fed time (per user) and if recently - cancel the next reminder

    # todo: send the photo to other responsible people
    # Notify partners if any
    # user = await db_manager.get_user(message.from_user.id)
    # if user and user.get("partners"):
    #     # TODO: Implement partner notification
    #     for partner_id in user.partners:
    #         message.forward(chat_id=partner_id)
    #     pass


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


@add_command("timezone", "Set your timezone")
@router.message(Command("timezone"))
async def timezone_setup(message: Message, state: FSMContext) -> None:
    """Setup user timezone"""
    await setup_timezone(message)


async def setup_timezone(message: Message) -> None:
    """Ask user for timezone and save it"""
    state = create_state(message.chat.id)

    while True:
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


@router.message(F.chat.type == "private")
async def handle_messages(message: Message) -> None:
    """Handle non-command messages"""
    # if message.chat.type == "private":
    await reply_safe(
        message,
        "This bot doesn't support casual chatting!\n\n"
        "Available commands:\n"
        "/start - Start the bot\n"
        "/setup - Setup feeding schedule\n"
        "/timezone - Set your timezone\n"
        "/fed - Register a feeding\n"
        "/stats - Show stats"
        "/full_stats - Show full stats"
        "/help - Show all commands",
    )
