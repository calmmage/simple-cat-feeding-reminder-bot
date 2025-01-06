from loguru import logger

from src.database import DatabaseManager
from src.routers.schedule import schedule_reminder


async def reload_schedules() -> None:
    """Reload all user schedules from database on bot startup"""
    dbm = DatabaseManager()

    # Get all schedules from database
    schedules = dbm.db.schedules.find({})

    async for schedule in schedules:
        user_id = schedule["user_id"]

        # Get user's timezone
        user = await dbm.get_user(user_id)
        if not user or not user.get("timezone"):
            logger.warning(f"User {user_id} has schedule but no timezone set, skipping...")
            continue

        # Schedule each reminder time
        for time in schedule["times"]:
            hour, minute = map(int, time.split(":"))

            try:
                await schedule_reminder(
                    chat_id=user_id,
                    hour=hour,
                    minute=minute,
                    reschedule_if_missed=True,
                    timezone=user["timezone"],
                )
                logger.info(
                    f"Restored schedule for user {user_id}: "
                    f"{hour:02d}:{minute:02d} {user['timezone']}"
                )
            except Exception as e:
                logger.error(
                    f"Failed to restore schedule for user {user_id} at "
                    f"{hour:02d}:{minute:02d}: {str(e)}"
                )
