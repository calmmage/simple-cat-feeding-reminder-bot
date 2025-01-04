from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from botspot.components.bot_commands_menu import add_command
from botspot.utils import send_safe
from botspot.utils.deps_getters import get_scheduler

router = Router()
# plan: dev/todo.md


@add_command("start", "Start the bot")
@router.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    """Send a welcome message when the command /start is issued"""
    # await reply_safe(
    #     message,
    #     f"Hello, {html.bold(message.from_user.full_name)}!\n\n"
    #     "This is a cat feeding reminder bot. "
    #     # f"Use /help to see available commands."
    # )
    #
    # 1: set up reminders in the scheduler.
    # 2: notify the user reminders are set.
    # 3: save the reminders in the database.
    # 4: make sure reminders are recovered from the database on restart.

    # 1: set up reminders in the scheduler.
    scheduler = get_scheduler()
    user_id = message.from_user.id
    scheduler.add_job(send_user_a_reminder, "interval", seconds=10, args=[user_id])
    # 2: notify the user reminders are set.
    await send_safe(user_id, "Reminders are set!")
    # todo: 3: save the reminders in the database.
    # todo: 4: make sure reminders are recovered from the database on restart.


# @add_command("help", "Show help")
# @router.message(Command("help"))
# async def command_help_handler(message: Message) -> None:
#     """Send a help message when the command /help is issued"""
#     await reply_safe(
#         message,
#         "This is a cat feeding reminder bot. "
#         f"Use /help to see available commands."
#     )


async def send_user_a_reminder(user_id: int) -> None:
    await send_safe(user_id, "Reminder: feed the cat")
