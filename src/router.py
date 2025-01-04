import json
import random
from datetime import datetime, timedelta

from aiogram import Router, html
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from botspot.components import ask_user
from botspot.components.ask_user_handler import ask_user_choice
from botspot.components.bot_commands_menu import add_command
from botspot.utils import reply_safe, send_safe
from botspot.utils.deps_getters import get_scheduler
from src.utils import create_state, repo_root

router = Router()
# plan: dev/todo.md

SCHEDULES = {
    "2 times": ["08:00", "20:00"],
    "3 times": ["08:00", "14:00", "20:00"],
    "4 times": ["08:00", "12:00", "16:00", "20:00"],
    "Manual": None,  # Not implemented yet
}


# @add_command("help", "Show help")
# @router.message(Command("help"))
# async def command_help_handler(message: Message) -> None:
#     """Send a help message when the command /help is issued"""
#     await reply_safe(
#         message,
#         "This is a cat feeding reminder bot. "
#         f"Use /help to see available commands."
#     )
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
    # if not message.from_user:
    #     await reply_safe(message, "Error: Could not identify user.")
    #     return

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
        )

    await reply_safe(
        message, f"Scheduled to feed your cat {choice} times per day:\n" f"{', '.join(schedule)}"
    )


async def send_reminder(chat_id: int) -> None:
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
        await send_safe(chat_id, "Time's up! Will remind again in 1 hour.")
        register_reminder(chat_id, datetime.now() + timedelta(hours=1))
        pass
        # step 3: if no (timeout) -> remind in 1 hour?


# todo: def register_fed
async def register_meal(message: Message) -> None:

    # step 2: if yes -> congratulate with random response from responses.json
    # Todo: check for 'yes' or 'no' in the response using gpt
    # Todo: add a button or command. Command should be /fed. good for now
    # todo: ask for a photo or video if missing

    responses_path = repo_root / "src" / "responses.json"
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


def register_reminder(user_id, timestamp) -> None:
    pass
