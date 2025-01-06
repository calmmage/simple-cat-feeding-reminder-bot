import os

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from botspot.components.bot_commands_menu import add_admin_command
from botspot.utils import reply_safe
from botspot.utils.deps_getters import get_database

from src.database import User

router = Router()

admin_user_id = os.getenv("ADMIN_USER_ID")


@add_admin_command("list_users", "List all users")
@router.message(Command("list_users"))
async def list_users(message: Message) -> None:
    if message.from_user.id != int(os.getenv("ADMIN_USER_ID", 0)):
        await reply_safe(message, "You are not authorized to use this command.")
        return
    db = get_database()
    users = await db.users.find().to_list(length=100)
    users_formatted = [User.model_validate(user) for user in users]
    # todo: format the output better
    # class User(BaseModel):
    #     user_id: int
    #     chat_id: int
    #     username: Optional[str]
    #     full_name: str
    #     timezone: Optional[str] = None
    #     partners: list[int] = []
    #     created_at: datetime
    #     updated_at: datetime
    user_list = ""

    for user in users_formatted:
        user_list += f"@{user.username} ({user.user_id}) - {user.full_name}\n"
    await reply_safe(message, f"Users: {user_list}")
