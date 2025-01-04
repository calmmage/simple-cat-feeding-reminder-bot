from pathlib import Path

from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey

# from aiogram.fsm.storage.redis import RedisStorage  # Optional, if using Redis

repo_root = Path(__file__).parent.parent


def create_state(chat_id: int) -> FSMContext:

    # Get the bot instance and storage from your dependencies
    from botspot.utils.deps_getters import get_bot  # Add this import if needed

    bot = get_bot()
    storage = bot.storage  # Get storage from your bot instance

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
