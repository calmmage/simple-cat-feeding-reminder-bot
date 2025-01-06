import json
import random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from botspot.components.ask_user_handler import ask_user_raw
from botspot.components.bot_commands_menu import add_command
from botspot.utils import reply_safe, send_safe
from loguru import logger

from src.routers.common import db_manager
from src.utils import create_state, repo_root
from src.utils.timezone_utils import get_user_local_time

router = Router()


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

        from src.routers.schedule import schedule_reminder

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
