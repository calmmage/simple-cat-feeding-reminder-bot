import json
import os
import random
from datetime import datetime, timedelta
from typing import Optional

from aiogram import Router, html
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from botspot.components.ask_user_handler import ask_user_choice, ask_user_raw
from botspot.components.bot_commands_menu import Visibility, add_command
from botspot.utils import answer_safe, reply_safe, send_safe
from botspot.utils.deps_getters import get_scheduler

from src.database import DatabaseManager
from src.utils import create_state, repo_root

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

    # If new user (no timezone set), we might want to ask for timezone
    if not user.get("timezone"):
        # TODO: Add timezone setup flow here
        pass

    await setup_schedule(message, state)


@add_command("setup", "Setup feeding schedule")
@router.message(Command("setup"))
async def setup_schedule(message: Message, state: FSMContext) -> None:
    """Setup feeding schedule"""
    choice = await ask_user_choice(
        message.chat.id, "Pick a schedule", list(SCHEDULES.keys()) + ["Cancel"], state, timeout=None
    )

    # if not choice or choice == "Cancel":
    #     await reply_safe(message, "Setup cancelled.")
    #     return
    if choice is None or choice == "Cancel":
        return

    if choice == "Manual":
        await reply_safe(message, "Manual schedule setup is not implemented yet.")
        return

    schedule = SCHEDULES[choice]

    assert message.from_user is not None

    # Save schedule to database
    await db_manager.save_user_schedule(message.from_user.id, choice, schedule)

    # Clear existing jobs
    clear_user_schedule(message.chat.id)

    # Add new jobs
    for time in schedule:
        hour, minute = map(int, time.split(":"))
        schedule_reminder(message.chat.id, hour=hour, minute=minute, reschedule_if_missed=True)

    # await answer_safe(
    #     message, f"Scheduled to feed your cat {choice} times per day:\n" f"{', '.join(schedule)}"
    # )

    # Send a test reminder right away
    await answer_safe(message, "Here's how the reminders will look:")
    await send_reminder(message.chat.id, reschedule_if_missed=False)


def clear_user_schedule(chat_id: int) -> None:
    """Clear all scheduled reminders for a user"""
    scheduler = get_scheduler()
    for job in scheduler.get_jobs():
        if job.id.startswith(f"feed_{chat_id}"):
            scheduler.remove_job(job.id)


def schedule_reminder(
    chat_id: int,
    timestamp: Optional[datetime] = None,
    *,
    hour: Optional[int] = None,
    minute: Optional[int] = None,
    reschedule_if_missed: bool = True,
) -> None:
    """Schedule a reminder - either one-time or recurring"""
    scheduler = get_scheduler()

    if timestamp is not None:  # One-time reminder
        job_id = f"followup_{chat_id}_{timestamp.strftime('%Y%m%d_%H%M')}"
        scheduler.add_job(
            send_reminder,
            "date",
            run_date=timestamp,
            id=job_id,
            args=[chat_id],
            kwargs={"reschedule_if_missed": reschedule_if_missed},
        )
    else:  # Recurring reminder
        job_id = f"feed_{chat_id}_{hour:02d}:{minute:02d}"
        scheduler.add_job(
            send_reminder,
            "cron",
            hour=hour,
            minute=minute,
            id=job_id,
            args=[chat_id],
            kwargs={"reschedule_if_missed": reschedule_if_missed},
        )


async def send_reminder(chat_id: int, reschedule_if_missed: bool = True) -> None:
    """Send feeding reminder"""
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
        await register_meal(response)
    else:
        reply_text = "Time's up!"
        if reschedule_if_missed:
            reply_text += " Will remind again in 1 hour."
            schedule_reminder(chat_id, timestamp=datetime.now() + timedelta(hours=1))
        await send_safe(chat_id, reply_text)


async def register_meal(message: Message) -> None:
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

    # Add hidden commands section for admin
    # Get bot info to check if user is owner
    # bot_info = await message.bot.get_me()
    # if message.from_user.id == bot_info.id:  # Only show to bot owner
    text += "\n<b>Hidden Commands:</b>\n"
    for cmd, info in commands.items():
        if info.visibility == Visibility.HIDDEN:
            text += f"/{cmd} - {info.description}\n"

        if message.from_user.id == int(os.getenv("ADMIN_USER_ID", 0)):
            if info.visibility == Visibility.ADMIN_ONLY:
                text += f"/{cmd} - {info.description}\n"

    await reply_safe(message, text)
