# File: main.py

import asyncio
import json
import os
from aiohttp import web
from bot import Bot
from pyrogram import idle
from plugins.cleanup import run_cleanup_and_notify
from plugins import web_server

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
    # 1. Initialize the bot instances as before
    apps = await main_logic()

    # 2. Set up the aiohttp web server
    web_app = await web_server(apps)
    app_runner = web.AppRunner(web_app)
    await app_runner.setup()

    # 3. Get the port from the environment variable for Heroku compatibility
    # Heroku will set the PORT env var. The default is for local testing.
    PORT = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(app_runner, "0.0.0.0", PORT)

    # 4. Start the web server and print a confirmation
    await site.start()
    print(f"✅ Web server successfully started on port {PORT}")

    # 5. Run the bot's background tasks and keep the bot clients alive concurrently.
    # idle() keeps the bot clients connected, and background_tasks runs your periodic cleanup.
    await asyncio.gather(
        background_tasks(apps),
        idle()
    )

if __name__ == "__main__":
    try:
        asyncio.run(runner())
    except KeyboardInterrupt:
        print("\nBot stopped manually.")
