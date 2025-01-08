from datetime import datetime
from typing import Optional

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from botspot import ask_user_choice
from botspot.components.bot_commands_menu import add_command
from botspot.utils import get_scheduler, reply_safe
from loguru import logger

from src.routers.common import SCHEDULES, db_manager
from src.routers.feeding import send_reminder
from src.utils.timezone_utils import convert_time_to_gmt

router = Router()


@add_command("setup", "Setup feeding schedule")
@router.message(Command("setup"))
async def setup_schedule(message: Message, state: FSMContext) -> None:
    """Setup feeding schedule"""
    choices = {k: f"{k} - {v}" for k, v in SCHEDULES.items()}
    choices["Cancel"] = "Cancel"
    choice = await ask_user_choice(message.chat.id, "Pick a schedule", choices, state, timeout=None)

    if choice is None or choice == "Cancel" or choice not in SCHEDULES:
        return

    if choice == "Manual":
        await reply_safe(message, "Manual schedule setup is not implemented yet.")
        return

    schedule = SCHEDULES[choice]
    assert message.from_user is not None

    # Clear existing schedule before setting up new one
    clear_user_schedule(message.chat.id)

    # Save new schedule to database
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
        if f"_{chat_id}_" in job.id:
            scheduler.remove_job(job.id)
        elif chat_id in job.args or chat_id in job.kwargs.values():
            logger.warning(f"Found job with chat_id in args or kwargs and not in id: {job.id}")
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
