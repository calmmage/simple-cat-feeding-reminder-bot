from datetime import datetime
from typing import Any, Dict, List, Optional

from aiogram.types import Message
from botspot.utils.deps_getters import get_database
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel


class User(BaseModel):
    user_id: int
    # chat_id: int
    username: Optional[str]
    full_name: str
    timezone: Optional[str] = None
    partners: list[int] = []
    created_at: datetime
    updated_at: datetime


class Schedule(BaseModel):
    type: str  # "2 times", "3 times", "4 times", "Manual"
    times: List[str]  # ["08:00", "20:00"]
    created_at: datetime
    updated_at: datetime


class Feeding(BaseModel):
    user_id: int
    timestamp: datetime
    schedule_type: str
    photo_id: Optional[str] = None
    video_id: Optional[str] = None
    partners_notified: List[int] = []


class DatabaseManager:
    @property
    def db(self) -> AsyncIOMotorDatabase:
        return get_database()

    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        return await self.db.users.find_one({"user_id": user_id})

    async def create_or_update_user(self, message: Message) -> Dict[str, Any]:
        """Create or update user from message"""
        user = message.from_user
        now = datetime.now()

        user_data = {
            "user_id": user.id,
            # "chat_id": message.chat.id,
            "username": user.username,
            "full_name": user.full_name,
            "updated_at": now,
        }

        # Try to update existing user
        result = await self.db.users.update_one(
            {"user_id": user.id},
            {
                "$set": user_data,
                "$setOnInsert": {
                    "timezone": None,
                    "partners": [],
                    "created_at": now,
                },
            },
            upsert=True,
        )

        if result.upserted_id:  # New user was created
            return await self.get_user(user.id)

        return await self.get_user(user.id)

    async def update_user_timezone(self, user_id: int, timezone: str) -> None:
        """Update user's timezone"""
        await self.db.users.update_one(
            {"user_id": user_id}, {"$set": {"timezone": timezone, "updated_at": datetime.now()}}
        )

    async def add_partner(self, user_id: int, partner_id: int) -> None:
        """Add partner to user's partners list"""
        await self.db.users.update_one(
            {"user_id": user_id},
            {"$addToSet": {"partners": partner_id}, "$set": {"updated_at": datetime.now()}},
        )

    async def save_user_schedule(self, user_id: int, schedule_type: str, times: List[str]) -> None:
        """Save user's feeding schedule"""
        now = datetime.now()
        await self.db.schedules.update_one(
            {"user_id": user_id},
            {
                "$set": {"type": schedule_type, "times": times, "updated_at": now},
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
        )

    async def get_user_schedule(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user's current schedule"""
        return await self.db.schedules.find_one({"user_id": user_id})

    async def log_feeding(
        self,
        user_id: int,
        schedule_type: str,
        photo_id: Optional[str] = None,
        video_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Log a feeding event"""
        feeding_data = {
            "user_id": user_id,
            "timestamp": datetime.now(),
            "schedule_type": schedule_type,
            "photo_id": photo_id,
            "video_id": video_id,
            "partners_notified": [],
        }
        result = await self.db.feedings.insert_one(feeding_data)
        return await self.db.feedings.find_one({"_id": result.inserted_id})

    async def get_user_feedings(
        self,
        user_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get user's feeding history"""
        query = {"user_id": user_id}
        if start_date or end_date:
            query["timestamp"] = {}
            if start_date:
                query["timestamp"]["$gte"] = start_date
            if end_date:
                query["timestamp"]["$lte"] = end_date

        cursor = self.db.feedings.find(query).sort("timestamp", -1).limit(limit)
        return await cursor.to_list(length=limit)

    async def mark_partners_notified(self, feeding_id: str, partner_ids: List[int]) -> None:
        """Mark that partners were notified about a feeding"""
        await self.db.feedings.update_one(
            {"_id": feeding_id}, {"$addToSet": {"partners_notified": {"$each": partner_ids}}}
        )
