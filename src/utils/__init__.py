import sys
from pathlib import Path

from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey

# from aiogram.fsm.storage.redis import RedisStorage  # Optional, if using Redis

repo_root = Path(__file__).parent.parent.parent


def create_state(chat_id: int) -> FSMContext:

    # Get the bot instance and storage from your dependencies
    from botspot.utils.deps_getters import get_bot, get_dispatcher  # Add this import if needed

    dp = get_dispatcher()
    bot = get_bot()
    storage = dp.storage

    # Create state context for the specific chat
    state = FSMContext(
        storage=storage,
        key=StorageKey(
            chat_id=chat_id,
            user_id=chat_id,  # You might want to adjust this if user_id is different
            bot_id=bot.id,
        ),
    )
    return state


def setup_logger(logger, level: str = "INFO"):
    logger.remove()  # Remove default handler
    logger.add(
        sink=sys.stderr,
        format="<level>{time:HH:mm:ss}</level> | <level>{message}</level>",
        colorize=True,
        level=level,
    )
