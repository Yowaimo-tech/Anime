# File: helper/database.py

import motor.motor_asyncio
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")

# --- Reverted to the simple verification structure ---
default_verify = {
    'is_verified': False,
    'verified_time': 0,
    'verify_token': "",
    'file_payload': ""
}

class MongoDB:
    _instances = {}

    def __new__(cls, uri: str, db_name: str, logger):
        if (uri, db_name) not in cls._instances:
            instance = super().__new__(cls)
            instance.client = motor.motor_asyncio.AsyncIOMotorClient(uri)
            instance.db = instance.client[db_name]
            instance.user_data = instance.db["users"]
            instance.pro_data = instance.db["pros"]
            instance.channel_data = instance.db["channels"]
            instance.settings_collection = instance.db['bot_settings']
            instance.stats_collection = instance.db['daily_stats']
            instance.verify_counts = instance.db["daily_verify_counts"]
            instance.LOGGER = logger
            cls._instances[(uri, db_name)] = instance
        return cls._instances[(uri, db_name)]

    # Channel Management Functions
    async def save_channel(self, channel_id: int):
        """Save channel to database"""
        try:
            await self.channel_data.update_one(
                {"_id": channel_id},
                {"$set": {"added_at": datetime.utcnow()}},
                upsert=True
            )
            # Also add to channels list in user_data
            channels = await self.get_channels()
            if channel_id not in channels:
                channels.append(channel_id)
                await self.user_data.update_one(
                    {"_id": 1},
                    {"$set": {"channels": channels}},
                    upsert=True
                )
            return True
        except Exception as e:
            self.LOGGER(__name__, "DB_CHANNEL").error(f"Failed to save channel {channel_id}: {e}")
            return False

    async def delete_channel(self, channel_id: int):
        """Delete channel from database"""
        try:
            # Remove from channel_data collection
            await self.channel_data.delete_one({"_id": channel_id})
            
            # Remove from channels list
            channels = await self.get_channels()
            if channel_id in channels:
                channels.remove(channel_id)
                await self.user_data.update_one(
                    {"_id": 1},
                    {"$set": {"channels": channels}},
                    upsert=True
                )
            return True
        except Exception as e:
            self.LOGGER(__name__, "DB_CHANNEL").error(f"Failed to delete channel {channel_id}: {e}")
            return False

    async def get_channels(self):
        """Get all channels from database"""
        try:
            user_doc = await self.user_data.find_one({"_id": 1})
            if user_doc and "channels" in user_doc:
                return user_doc["channels"]
            return []
        except Exception as e:
            self.LOGGER(__name__, "DB_CHANNEL").error(f"Failed to get channels: {e}")
            return []

    async def save_encoded_link(self, channel_id: int, encoded_str: str):
        """Save encoded link for channel"""
        try:
            await self.channel_data.update_one(
                {"_id": channel_id},
                {"$set": {"encoded_link": encoded_str}},
                upsert=True
            )
            return True
        except Exception as e:
            self.LOGGER(__name__, "DB_CHANNEL").error(f"Failed to save encoded link for {channel_id}: {e}")
            return False

    async def save_encoded_request_link(self, channel_id: int, encoded_str: str):
        """Save encoded request link for channel"""
        try:
            await self.channel_data.update_one(
                {"_id": channel_id},
                {"$set": {"encoded_request": encoded_str}},
                upsert=True
            )
            return True
        except Exception as e:
            self.LOGGER(__name__, "DB_CHANNEL").error(f"Failed to save encoded request for {channel_id}: {e}")
            return False

    async def get_channel_info(self, channel_id: int):
        """Get channel information"""
        try:
            return await self.channel_data.find_one({"_id": channel_id})
        except Exception as e:
            self.LOGGER(__name__, "DB_CHANNEL").error(f"Failed to get channel info for {channel_id}: {e}")
            return None

    async def add_channel_user(self, channel_id: int, user_id: int):
        """Add user to channel's user list"""
        try:
            await self.channel_data.update_one(
                {"_id": channel_id}, 
                {"$addToSet": {"users": user_id}}, 
                upsert=True
            )
            return True
        except Exception as e:
            self.LOGGER(__name__, "DB_CHANNEL").error(f"Failed to add user {user_id} to channel {channel_id}: {e}")
            return False

    async def remove_channel_user(self, channel_id: int, user_id: int):
        """Remove user from channel's user list"""
        try:
            await self.channel_data.update_one(
                {"_id": channel_id}, 
                {"$pull": {"users": user_id}}
            )
            return True
        except Exception as e:
            self.LOGGER(__name__, "DB_CHANNEL").error(f"Failed to remove user {user_id} from channel {channel_id}: {e}")
            return False

    async def get_channel_users(self, channel_id: int):
        """Get all users in a channel"""
        try:
            channel = await self.channel_data.find_one({"_id": channel_id})
            return channel.get("users", []) if channel else []
        except Exception as e:
            self.LOGGER(__name__, "DB_CHANNEL").error(f"Failed to get users for channel {channel_id}: {e}")
            return []

    async def is_user_in_channel(self, channel_id: int, user_id: int):
        """Check if user is in channel"""
        try:
            channel = await self.channel_data.find_one(
                {"_id": channel_id, "users": user_id}
            )
            return channel is not None
        except Exception as e:
            self.LOGGER(__name__, "DB_CHANNEL").error(f"Failed to check user in channel {channel_id}: {e}")
            return False

    # Existing functions from your original code
    async def get_verify_status(self, user_id: int):
        user = await self.user_data.find_one({'_id': user_id})
        return user.get('verify_status', default_verify) if user else default_verify

    async def update_verify_status(self, user_id: int, status: dict):
        await self.user_data.update_one({'_id': user_id}, {'$set': {'verify_status': status}}, upsert=True)

    async def reset_all_verify_counts(self):
        today_str = datetime.utcnow().strftime("%Y-%m-%d")
        await self.verify_counts.delete_many({'_id': {'$lt': today_str}})

    async def increment_verify_count(self):
        today_str = datetime.utcnow().strftime("%Y-%m-%d")
        await self.verify_counts.update_one({'_id': today_str}, {'$inc': {'count': 1}}, upsert=True)

    async def get_verify_stats(self):
        today_str = datetime.utcnow().strftime("%Y-%m-%d")
        yesterday_str = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
        today_data = await self.verify_counts.find_one({'_id': today_str})
        yesterday_data = await self.verify_counts.find_one({'_id': yesterday_str})
        today_count = today_data.get('count', 0) if today_data else 0
        yesterday_count = yesterday_data.get('count', 0) if yesterday_data else 0
        return today_count, yesterday_count

    async def get_user_state(self, user_id: int):
        try:
            user_doc = await self.user_data.find_one({'_id': user_id}, {'ban': 1})
            pro_doc = await self.pro_data.find_one({'_id': user_id})
            if not user_doc:
                await self.add_user(user_id)
                user_doc = {}
            is_pro = False
            expires_at = None
            if pro_doc:
                expires_at = pro_doc.get('expires_at')
                is_pro = True
                if expires_at:
                    if expires_at.tzinfo is None:
                        expires_at = expires_at.replace(tzinfo=timezone.utc)
                    if datetime.now(timezone.utc) > expires_at:
                        is_pro = False
            state = {
                'banned': user_doc.get('ban', False),
                'is_pro': is_pro
            }
            return state, expires_at
        except Exception as e:
            self.LOGGER(__name__, "DB_STATE").error(f"Failed to get user state for {user_id}: {e}", exc_info=True)
            return None, None

    async def cleanup_expired_pros(self):
        expired_user_ids = []
        try:
            now_utc = datetime.now(timezone.utc)
            expired_users_cursor = self.pro_data.find({'expires_at': {'$ne': None, '$lt': now_utc}})
            async for user_doc in expired_users_cursor:
                user_id = user_doc['_id']
                expired_user_ids.append(user_id)
                await self.remove_pro(user_id)
            if expired_user_ids:
                self.LOGGER(__name__, "DB_CLEANUP").info(f"Cleaned up {len(expired_user_ids)} expired pro users.")
            return expired_user_ids
        except Exception as e:
            self.LOGGER(__name__, "DB_CLEANUP").error(f"Error during expired pro user cleanup: {e}", exc_info=True)
            return []

    async def add_user(self, user_id: int, ban_status: bool = False):
        try:
            await self.user_data.update_one({'_id': user_id}, {'$set': {'ban': ban_status}}, upsert=True)
        except Exception as e:
            self.LOGGER(__name__, "DB_USER").error(f"Failed to add/update user {user_id}: {e}")

    async def present_user(self, user_id: int):
        return await self.user_data.find_one({'_id': user_id}) is not None

    async def del_user(self, user_id: int):
        await self.user_data.delete_one({'_id': user_id})

    async def full_userbase(self):
        return [doc['_id'] async for doc in self.user_data.find({}, {'_id': 1})]

    async def is_pro(self, user_id: int):
        state, _ = await self.get_user_state(user_id)
        return state.get('is_pro', False) if state else False

    async def is_banned(self, user_id: int):
        state, _ = await self.get_user_state(user_id)
        return state.get('banned', False) if state else False

    async def get_pro_user(self, user_id: int):
        return await self.pro_data.find_one({'_id': user_id})

    async def increment_shortener_clicks(self):
        today_str = datetime.utcnow().strftime("%Y-%m-%d")
        await self.stats_collection.update_one({'_id': today_str}, {'$inc': {'clicks': 1}}, upsert=True)

    async def get_stats(self):
        today_str = datetime.utcnow().strftime("%Y-%m-%d")
        yesterday_str = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
        today_data = await self.stats_collection.find_one({'_id': today_str})
        yesterday_data = await self.stats_collection.find_one({'_id': yesterday_str})
        today_clicks = today_data.get('clicks', 0) if today_data else 0
        yesterday_clicks = yesterday_data.get('clicks', 0) if yesterday_data else 0
        return today_clicks, yesterday_clicks

    async def load_settings(self, session_name: str):
        return await self.settings_collection.find_one({'_id': session_name})

    async def save_settings(self, session_name: str, settings: dict):
        await self.settings_collection.update_one({'_id': session_name}, {'$set': settings}, upsert=True)

    async def set_channels(self, channels: list[int]):
        await self.user_data.update_one({"_id": 1}, {"$set": {"channels": channels}}, upsert=True)

    async def add_pro(self, user_id, expires_at=None):
        try:
            await self.pro_data.update_one({'_id': user_id}, {'$set': {'expires_at': expires_at}}, upsert=True)
            return True
        except Exception as e:
            self.LOGGER(__name__, "DB_PRO").error(f"Failed to add pro user {user_id}: {e}")
            return False

    async def remove_pro(self, user_id: int):
        try:
            await self.pro_data.delete_one({'_id': user_id})
            return True
        except Exception as e:
            self.LOGGER(__name__, "DB_PRO").error(f"Failed to remove pro user {user_id}: {e}")
            return False

    async def get_pros_list(self):
        return [doc async for doc in self.pro_data.find()]

    async def ban_user(self, user_id: int):
        await self.user_data.update_one({'_id': user_id}, {'$set': {'ban': True}}, upsert=True)

    async def unban_user(self, user_id: int):
        await self.user_data.update_one({'_id': user_id}, {'$set': {'ban': False}}, upsert=True)
