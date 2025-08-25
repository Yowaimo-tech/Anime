# @NaapaExtra

from pyrogram import Client, filters
from pyrogram.types import Message

@Client.on_message(filters.command('stats') & filters.private)
async def stats_command(client: Client, message: Message):
    if message.from_user.id not in client.admins:
        return await message.reply("You do not have permission to use this command.")

    try:
        today_verifies, yesterday_verifies = await client.mongodb.get_verify_stats()
        
        total_users = await client.mongodb.full_userbase()
        
        stats_message = (
            f"📊 **Bot Statistics**\n\n"
            f"👤 **User Base:**\n"
            f"   - Total Users: `{len(total_users)}`\n\n"
            f"✅ **Token Verifications:**\n"
            f"   - **Today:** `{today_verifies}` verifications\n"
            f"   - **Yesterday:** `{yesterday_verifies}` verifications"
        )

        await message.reply_text(stats_message)

    except Exception as e:
        client.LOGGER(__name__, client.name).error(f"Error fetching stats: {e}")
        await message.reply_text("An error occurred while fetching statistics.")
