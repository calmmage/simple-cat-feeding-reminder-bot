import json
import random
from aiogram import Router, html
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from datetime import datetime, timedelta
from src.utils import create_state, repo_root

from botspot.components import ask_user
from botspot.components.ask_user_handler import ask_user_choice
from botspot.components.bot_commands_menu import add_command
from botspot.utils import reply_safe, send_safe
from botspot.utils.deps_getters import get_scheduler

router = Router()

# plan: dev/todo.md

SCHEDULES = {
    "2 times": ["08:00", "20:00"],
    "3 times": ["08:00", "14:00", "20:00"],
    "4 times": ["08:00", "12:00", "16:00", "20:00"],
    "Manual": None,  # Not implemented yet
}


@add_command("start", "Start the bot")
@router.message(CommandStart())
async def command_start_handler(message: Message, state: FSMContext) -> None:
    """Send a welcome message when the command /start is issued"""
    await reply_safe(
        message,
        f"Hello, {html.bold(message.from_user.full_name)}!\n\n"
        "This is a cat feeding reminder bot. ",
        # f"Use /help to see available commands."
    )

    await setup_schedule(message, state)


@add_command("setup", "Setup feeding schedule")
@router.message(Command("setup"))
async def setup_schedule(message: Message, state: FSMContext) -> None:
    """Setup feeding schedule"""
    choice = await ask_user_choice(
        message.chat.id, "Pick a schedule", list(SCHEDULES.keys()) + ["Cancel"], state, timeout=None
    )

    if not choice or choice == "Cancel":
        await reply_safe(message, "Setup cancelled.")
        return

    if choice == "Manual":
        await reply_safe(message, "Manual schedule setup is not implemented yet.")
        return

    schedule = SCHEDULES[choice]
    scheduler = get_scheduler()

    # Clear existing jobs for this user
    for job in scheduler.get_jobs():
        if job.id.startswith(f"feed_{message.from_user.id}"):
            scheduler.remove_job(job.id)

    # Add new jobs
    for time in schedule:
        hour, minute = map(int, time.split(":"))
        scheduler.add_job(
            send_reminder,
            "cron",
            hour=hour,
            minute=minute,
            id=f"feed_{message.from_user.id}_{time}",
            args=[message.chat.id],
            # kwargs={"reschedule_if_missed": True}  # Regular reminders should reschedule
        )

    await reply_safe(
        message, f"Scheduled to feed your cat {choice} times per day:\n" f"{', '.join(schedule)}"
    )

    # Send a test reminder right away
    await reply_safe(message, "Here's how the reminders will look:")
    await send_reminder(
        message.chat.id, reschedule_if_missed=False
    )  # Test reminder shouldn't reschedule


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
    response = await ask_user(
        chat_id=chat_id,
        question="Time to feed your cat! Did you?",
        state=state,
        timeout=300.0,
        return_raw=True,
    )

    if response:
        await register_meal(response)
    else:
        # notify user of the time out
        # todo: fix the message as well
        reply_text = "Time's up!"
        if reschedule_if_missed:
            reply_text += " Will remind again in 1 hour."
            register_reminder(chat_id, datetime.now() + timedelta(hours=1))

        await send_safe(chat_id, reply_text)


async def register_meal(message: Message) -> None:

    # step 2: if yes -> congratulate with random response from responses.json
    # Todo: check for 'yes' or 'no' in the response using gpt
    # Todo: add a button or command. Command should be /fed. good for now
    # todo: ask for a photo or video if missing

    responses_path = repo_root / "src" / "resources" / "responses.json"
    with open(responses_path, encoding="utf-8") as file:
        responses = json.load(file)

    reply_text = random.choice(responses["feed_success"])

    # step 2.a if with photo
    # check if image has media
    if not (message.photo or message.video):
        # step 2.b if without photo
        reply_text += "\nNo photo though? :("
        # todo: request, not just ask

    await reply_safe(message, reply_text)

    # bonus: track last fed time (per user) and if recently - cancel the next reminder

    # todo: save timestamp
    # todo: send the photo to other responsible people


def register_reminder(chat_id: int, timestamp: datetime) -> None:
    """Schedule a follow-up reminder"""
    scheduler = get_scheduler()

    # Create a unique job ID for this follow-up reminder
    job_id = f"followup_{chat_id}_{timestamp.strftime('%Y%m%d_%H%M')}"

    # Add one-time job for the follow-up reminder
    scheduler.add_job(
        send_reminder,
        "date",  # Run once at specific time
        run_date=timestamp,
        id=job_id,
        args=[chat_id],
        kwargs={"reschedule_if_missed": True},  # Allow rescheduling for follow-ups
    )


@add_command("help", "Show available commands")
@router.message(Command("help"))
async def help_command(message: Message) -> None:
    """Show help message with available commands"""
    from botspot.components.bot_commands_menu import commands

    # Main commands section
    text = "🐱 <b>Cat Feeding Bot Commands</b>\n\n"
    text += "<b>Main Commands:</b>\n"
    for cmd, info in commands.items():
        if not info.hidden:
            text += f"/{cmd} - {info.description}\n"

    # Add hidden commands section for admin
    # Get bot info to check if user is owner
    # bot_info = await message.bot.get_me()
    # if message.from_user.id == bot_info.id:  # Only show to bot owner
    text += "\n<b>Hidden Commands:</b>\n"
    for cmd, info in commands.items():
        if info.hidden:
            text += f"/{cmd} - {info.description}\n"

    await reply_safe(message, text)
