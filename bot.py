# File: bot.py

from pyrogram import Client
from pyrogram.enums import ParseMode
import sys
from datetime import datetime
import config
from helper import MongoDB
from apscheduler.schedulers.asyncio import AsyncIOScheduler

version = "v1.0.0"

async def daily_reset_task(bot_instance):
    bot_instance.LOGGER(__name__, bot_instance.session_name).debug("SCHEDULER: Resetting daily verification counts.")
    await bot_instance.mongodb.reset_all_verify_counts()

# Reverted: Removed ad_wait_time and bypass_timeout from __init__
class Bot(Client):
    def __init__(self, session, workers, db, fsub, token, admins, messages, auto_del, db_uri, db_name, api_id, api_hash, protect, disable_btn):
        super().__init__(
            name=session,
            api_hash=api_hash,
            api_id=api_id,
            plugins={"root": "plugins"},
            workers=workers,
            bot_token=token
        )
        self.LOGGER = config.LOGGER
        self.initial_config = {
            "session": session, "workers": workers, "db": db, "fsub": fsub,
            "token": token, "admins": admins, "messages": messages, "auto_del": auto_del,
            "db_uri": db_uri, "db_name": db_name, "api_id": api_id, "api_hash": api_hash,
            "protect": protect, "disable_btn": disable_btn, "short_url": config.SHORT_URL, "short_api": config.SHORT_API
        }
        
        self.session_name = session
        self.owner = config.OWNER_ID
        self.mongodb = MongoDB(db_uri, db_name, self.LOGGER)
        self.uptime = datetime.now()
        self.req_channels = []
        self.fsub_dict = {}
        self.user_cache = {}
        self.scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")
        
        self.verify_expire = config.VERIFY_EXPIRE

    # Reverted: Removed ad_wait_time and bypass_timeout from settings
    def get_current_settings(self):
        return {
            "admins": self.admins,
            "messages": self.messages,
            "auto_del": self.auto_del,
            "protect": self.protect,
            "disable_btn": self.disable_btn,
            "reply_text": self.reply_text,
            "fsub": self.fsub,
            "short_url": self.short_url,
            "short_api": self.short_api,
            "verify_expire": self.verify_expire
        }

    async def start(self):
        await super().start()
        
        file_config = self.initial_config.copy()
        db_settings = await self.mongodb.load_settings(self.session_name)

        if db_settings:
            final_config = file_config
            final_config.update(db_settings)
            final_messages = file_config.get('messages', {}).copy()
            final_messages.update(db_settings.get('messages', {}))
            final_config['messages'] = final_messages

            self.admins = final_config.get("admins")
            self.messages = final_config.get("messages")
            self.auto_del = final_config.get("auto_del")
            self.protect = final_config.get("protect")
            self.disable_btn = final_config.get("disable_btn")
            self.fsub = final_config.get("fsub")
            self.short_url = final_config.get("short_url")
            self.short_api = final_config.get("short_api")
            self.reply_text = final_config.get("messages", {}).get('REPLY', '')
            self.verify_expire = final_config.get("verify_expire", config.VERIFY_EXPIRE)
        else:
            self.admins = file_config['admins']
            self.messages = file_config['messages']
            self.auto_del = file_config['auto_del']
            self.protect = file_config['protect']
            self.disable_btn = file_config['disable_btn']
            self.fsub = file_config['fsub']
            self.short_url = file_config['short_url']
            self.short_api = file_config['short_api']
            self.reply_text = file_config['messages'].get('REPLY', '')
            self.verify_expire = config.VERIFY_EXPIRE

        await self.mongodb.save_settings(self.session_name, self.get_current_settings())

        if self.owner not in self.admins:
            self.admins.append(self.owner)

        self.scheduler.add_job(daily_reset_task, "cron", hour=0, minute=0, args=[self])
        self.scheduler.start()

        usr_bot_me = await self.get_me()
        
        if len(self.fsub) > 0:
            for channel in self.fsub:
                try:
                    chat = await self.get_chat(channel[0])
                    name = chat.title
                    link = chat.invite_link or (await self.create_chat_invite_link(channel[0], creates_join_request=channel[1])).invite_link
                    self.fsub_dict[channel[0]] = [name, link, channel[1], channel[2]]
                    if channel[1]: self.req_channels.append(channel[0])
                except Exception as e: self.LOGGER(__name__, self.session_name).warning(f"F-Sub error for channel {channel[0]}: {e}")
            await self.mongodb.set_channels(self.req_channels)

        try:
            self.db = self.initial_config['db']
            self.db_channel = await self.get_chat(self.db)
            test = await self.send_message(chat_id=self.db_channel.id, text="Bot testing message...")
            await test.delete()
        except Exception as e:
            self.LOGGER(__name__, self.session_name).warning(e)
            self.LOGGER(__name__, self.session_name).warning(f"Make sure bot is Admin in DB Channel: {self.db}")
            sys.exit()
            
        self.username = usr_bot_me.username
        self.LOGGER(__name__, self.session_name).info("Bot Started Successfully!")

    async def stop(self, *args):
        await super().stop()
        self.LOGGER(__name__, self.session_name).info("Bot stopped.")
