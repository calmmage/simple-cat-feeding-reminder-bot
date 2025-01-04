from os import getenv

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from botspot.core.bot_manager import BotManager
from dotenv import load_dotenv

from src.router import router

load_dotenv()
TOKEN = getenv("TELEGRAM_BOT_TOKEN")
if TOKEN is None or TOKEN == "":
    raise ValueError("TELEGRAM_BOT_TOKEN is not set")

dp = Dispatcher()
dp.include_router(router)


async def main() -> None:
    # Initialize Bot instance with a default parse mode
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    # Initialize BotManager with default components
    bm = BotManager(
        bot=bot,
        error_handler={"enabled": True},
        ask_user={"enabled": True},
        bot_commands_menu={"enabled": True},
        database={"enabled": True},
    )

    # Setup dispatcher with our components
    bm.setup_dispatcher(dp)

    # Start polling
    await dp.start_polling(bot)
