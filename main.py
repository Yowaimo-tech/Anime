# File: main.py

import asyncio
import json
from bot import Bot
from pyrogram import idle
from plugins.cleanup import run_cleanup_and_notify

async def background_tasks(bots):
    while True:
        for bot_instance in bots:
            bot_instance.LOGGER(__name__, bot_instance.session_name).debug("BACKGROUND_TASK: Triggering scheduled cleanup.")
            await run_cleanup_and_notify(bot_instance)
        await asyncio.sleep(3600)

default_messages = {
    'START': '<b>Hi There...! 💥\n\nI am a file-store bot.\nI can generate links directly with no problems\nMy Owner: @MRSungCHinwOO</b>',
    'FSUB': '', 'ABOUT': 'ABOUT MSG', 'REPLY': 'reply_text',
    'START_PHOTO': '', 'FSUB_PHOTO': '', 'VERIFY_PHOTO': ''
}

async def main_logic():
    apps = []
    with open("setup.json", "r") as f:
        setups = json.load(f)

    for config in setups:
        # Reverted: Removed ad_wait_time and bypass_timeout
        bot_instance = Bot(
            session=config["session"],
            workers=config.get("workers", 8),
            db=config["db"],
            fsub=config.get("fsubs", []),
            token=config["token"],
            admins=config.get("admins", []),
            messages=config.get("messages", default_messages),
            auto_del=config.get("auto_del", 0),
            db_uri=config["db_uri"],
            db_name=config["db_name"],
            api_id=int(config["api_id"]),
            api_hash=config["api_hash"],
            protect=config.get("protect", False),
            disable_btn=config.get("disable_btn", True)
        )
        apps.append(bot_instance)

    await asyncio.gather(*[app.start() for app in apps])
    print("All bots and background tasks have started successfully!")
    return apps

async def runner():
    apps = await main_logic()
    await asyncio.gather(idle(), background_tasks(apps))

if __name__ == "__main__":
    try: asyncio.run(runner())
    except KeyboardInterrupt: print("\nBot stopped manually.")
