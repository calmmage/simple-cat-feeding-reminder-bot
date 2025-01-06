from os import getenv

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from botspot.core.bot_manager import BotManager
from dotenv import load_dotenv

from src.routers.admin import router as admin_router
from src.routers.chat import router as chat_router
from src.routers.dev import router as dev_router
from src.routers.feeding import router as feeding_router
from src.routers.info import router as info_router
from src.routers.schedule import router as schedule_router
from src.routers.settings import router as settings_router
from src.routers.start import router as start_router
from src.startup_tasks import reload_schedules

# from src.routers.partners import router as partners_router

load_dotenv()
TOKEN = getenv("TELEGRAM_BOT_TOKEN")
if TOKEN is None or TOKEN == "":
    raise ValueError("TELEGRAM_BOT_TOKEN is not set")

dp = Dispatcher()
dp.include_router(dev_router)
dp.include_router(admin_router)
# dp.include_router(partners_router)
dp.include_router(info_router)
dp.include_router(feeding_router)
dp.include_router(schedule_router)
dp.include_router(settings_router)
dp.include_router(start_router)
dp.include_router(chat_router)


async def main() -> None:
    # Log server timezone on startup
    # Initialize Bot instance with a default parse mode
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    # Add startup handler
    @dp.startup()
    async def on_startup() -> None:
        await reload_schedules()

    # Initialize BotManager with default components
    bm = BotManager(
        bot=bot,
        dispatcher=dp,
        error_handler={"enabled": True},
        ask_user={"enabled": True},
        bot_commands_menu={"enabled": True},
        database={"enabled": True},
    )

    # Setup dispatcher with our components
    bm.setup_dispatcher(dp)

    # Start polling
    await dp.start_polling(bot)
