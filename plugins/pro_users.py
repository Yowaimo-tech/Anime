from pyrogram import Client, filters
from pyrogram.types import Message
from datetime import datetime, timedelta, timezone
from pyrogram.errors import PeerIdInvalid, UserIsBlocked, InputUserDeactivated
from zoneinfo import ZoneInfo

from bot import Bot
import config  # Corrected import

# Define the Indian Standard Time zone
IST = ZoneInfo("Asia/Kolkata")

#========================================================================#

@Client.on_message(filters.command('add_premium') & filters.private)
async def add_premium_command(client: Bot, message: Message):
    # Check if user is owner or admin
    if message.from_user.id != config.OWNER_ID and message.from_user.id not in config.ADMINS:
        await message.reply_text("❌ ᴏɴʟʏ ᴏᴡɴᴇʀ ᴀɴᴅ ᴀᴅᴍɪɴs ᴄᴀɴ ᴜsᴇ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ.")
        return

    if len(message.command) < 2:
        await message.reply_text(
            "🥂 ᴜsᴀɢᴇ:\n/add_premium <ᴜsᴇʀ_ɪᴅ> [ᴅᴜʀᴀᴛɪᴏɴ] [s/ᴍ/ʜ/ᴅ/ʏ]\n\n"
            "🎩 ᴇxᴀᴍᴘʟᴇs:\n"
            "🌀 /add_premium 123456789 — ᴘᴇʀᴍᴀɴᴇɴᴛ\n"
            "☔ /add_premium 123456789 2 ᴅ — 2 ᴅᴀʏs"
        )
        return

    try:
        user_id_to_add = int(message.command[1])
    except ValueError:
        await message.reply_text("❌ ɪɴᴠᴀʟɪᴅ ᴜsᴇʀ ɪᴅ.")
        return

    expires_at_ist_display = None
    action_text = "ᴘᴇʀᴍᴀɴᴇɴᴛʟʏ ᴀᴜᴛʜᴏʀɪᴢᴇᴅ"
    is_permanent = True

    # Handle temporary subscription if duration is provided
    if len(message.command) == 4:
        is_permanent = False
        try:
            amount = int(message.command[2])
            unit = message.command[3].lower()
            delta = timedelta()

            if unit == "s": delta = timedelta(seconds=amount)
            elif unit == "m": delta = timedelta(minutes=amount)
            elif unit == "h": delta = timedelta(hours=amount)
            elif unit == "d": delta = timedelta(days=amount)
            elif unit == "y": delta = timedelta(days=amount * 365)
            else:
                return await message.reply_text("❌ ɪɴᴠᴀʟɪᴅ ᴛɪᴍᴇ ᴜɴɪᴛ. ᴜsᴇ: s/ᴍ/ʜ/ᴅ/ʏ.")

            now_ist = datetime.now(IST)
            start_date_ist = now_ist
            action_text = "ʀᴇɴᴇᴡᴇᴅ"

            pro_doc = await client.mongodb.get_pro_user(user_id_to_add)
            if pro_doc:
                existing_expires_at = pro_doc.get('expires_at')
                if existing_expires_at:
                    existing_expires_at_ist = existing_expires_at.astimezone(IST)
                    if existing_expires_at_ist > now_ist:
                        start_date_ist = existing_expires_at_ist
                        action_text = "ᴇxᴛᴇɴᴅᴇᴅ"

            expires_at_ist_display = start_date_ist + delta
            expires_at_utc = expires_at_ist_display.astimezone(timezone.utc)
            await client.mongodb.add_pro(user_id_to_add, expires_at_utc)

        except Exception as e:
            await message.reply_text(f"❌ ᴀɴ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ ᴅᴜʀɪɴɢ ᴀᴜᴛʜᴏʀɪᴢᴀᴛɪᴏɴ: {e}")
            client.LOGGER(__name__, "ADD_PREMIUM").error(f"Error: {e}", exc_info=True)
            return
    else:
        # Handle permanent subscription
        await client.mongodb.add_pro(user_id_to_add, expires_at=None)

    # --- Notification Logic ---
    admin_reply_text = f"🎋 ᴜsᴇʀ <code>{user_id_to_add}</code> sᴜʙsᴄʀɪᴘᴛɪᴏɴ ʜᴀs ʙᴇᴇɴ {action_text.lower()}"
    if expires_at_ist_display:
        admin_reply_text += f" ᴜɴᴛɪʟ {expires_at_ist_display.strftime('%ᴅ %ʙ %ʏ, %ʜ:%ᴍ %ᴢ')}."

    try:
        if is_permanent:
            await client.send_message(user_id_to_add, "🎉 **ᴄᴏɴɢʀᴀᴛᴜʟᴀᴛɪᴏɴs!** 🥂\n\nʏᴏᴜ ʜᴀᴠᴇ ʙᴇᴇɴ ɢʀᴀɴᴛᴇᴅ ᴘᴇʀᴍᴀɴᴇɴᴛ ᴘʀᴇᴍɪᴜᴍ ᴀᴄᴄᴇss. ☔")
        else:
            expiry_text = expires_at_ist_display.strftime('%ᴅ %ʙ %ʏ ᴀᴛ %ɪ:%ᴍ %ᴘ %ᴢ')
            await client.send_message(user_id_to_add, f"🎉 **ᴄᴏɴɢʀᴀᴛᴜʟᴀᴛɪᴏɴs! ʏᴏᴜ ᴀʀᴇ ɴᴏᴡ ᴀ ᴘʀᴇᴍɪᴜᴍ ᴜsᴇʀ.** 🍥\n\nʏᴏᴜʀ ᴀᴄᴄᴇss ɪs ᴠᴀʟɪᴅ ᴜɴᴛɪʟ: **{expiry_text}** ⛱️")
        
        admin_reply_text += "\n\nᴜsᴇʀ ʜᴀs ʙᴇᴇɴ ɴᴏᴛɪғɪᴇᴅ. 🍷"
    except (UserIsBlocked, InputUserDeactivated, PeerIdInvalid):
        admin_reply_text += "\n\nᴄᴏᴜʟᴅ ɴᴏᴛ ɴᴏᴛɪғʏ ᴛʜᴇ ᴜsᴇʀ (ᴛʜᴇʏ ᴍᴀʏ ʜᴀᴠᴇ ʙʟᴏᴄᴋᴇᴅ ᴛʜᴇ ʙᴏᴛ). 🌀"
    except Exception as e:
        client.LOGGER(__name__, "ADD_PREMIUM_NOTIFY").error(f"Failed to notify user {user_id_to_add}: {e}")
        admin_reply_text += f"\n\nᴀɴ ᴜɴᴇxᴘᴇᴄᴛᴇᴅ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ ᴡʜɪʟᴇ ᴛʀʏɪɴɢ ᴛᴏ ɴᴏᴛɪғʏ ᴛʜᴇ ᴜsᴇʀ. 🎋"
    
    await message.reply_text(admin_reply_text)


#========================================================================#

@Client.on_message(filters.command('rev_premium') & filters.private)
async def rev_premium_command(client: Bot, message: Message):
    # Check if user is owner or admin
    if message.from_user.id != config.OWNER_ID and message.from_user.id not in config.ADMINS:
        await message.reply_text("❌ ᴏɴʟʏ ᴏᴡɴᴇʀ ᴀɴᴅ ᴀᴅᴍɪɴs ᴄᴀɴ ᴜsᴇ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ.")
        return

    if len(message.command) != 2:
        return await message.reply_text("🌀 ᴜsᴀɢᴇ: /rev_premium <ᴜsᴇʀɪᴅ>")

    try:
        user_id_to_remove = int(message.command[1])
    except ValueError:
        return await message.reply_text("❌ ɪɴᴠᴀʟɪᴅ ᴜsᴇʀ ɪᴅ. ᴘʟᴇᴀsᴇ ᴄʜᴇᴄᴋ ᴀɢᴀɪɴ...!")

    if not await client.mongodb.get_pro_user(user_id_to_remove):
        return await message.reply_text(f"☔ ᴜsᴇʀ <code>{user_id_to_remove}</code> ɪs ɴᴏᴛ ɪɴ ᴛʜᴇ ᴘʀᴇᴍɪᴜᴍ ʟɪsᴛ.")

    await client.mongodb.remove_pro(user_id_to_remove)
    
    user_name = f"<code>{user_id_to_remove}</code>"
    try:
        user = await client.get_users(user_id_to_remove)
        user_name = user.mention
    except (PeerIdInvalid, IndexError):
        pass

    await message.reply_text(f"🍥 ᴜsᴇʀ {user_name} ʜᴀs ʙᴇᴇɴ ʀᴇᴍᴏᴠᴇᴅ ғʀᴏᴍ ᴘʀᴇᴍɪᴜᴍ ᴜsᴇʀs! ⛱️")

    try:
        await client.send_message(user_id_to_remove, "🎋 ʏᴏᴜʀ ᴘʀᴇᴍɪᴜᴍ ᴍᴇᴍʙᴇʀsʜɪᴘ ʜᴀs ʙᴇᴇɴ ʀᴇᴠᴏᴋᴇᴅ.\n\nᴛᴏ ʀᴇɴᴇᴡ ᴛʜᴇ ᴍᴇᴍʙᴇʀsʜɪᴘ, ᴄᴏɴᴛᴀᴄᴛ ᴛʜᴇ ᴏᴡɴᴇʀ. 🍷")
    except (UserIsBlocked, InputUserDeactivated, PeerIdInvalid):
        await message.reply_text(f"🌀 ᴄᴏᴜʟᴅ ɴᴏᴛ ɴᴏᴛɪғʏ ᴛʜᴇ ᴜsᴇʀ (ᴛʜᴇʏ ᴍᴀʏ ʜᴀᴠᴇ ʙʟᴏᴄᴋᴇᴅ ᴛʜᴇ ʙᴏᴛ ᴏʀ ʜᴀᴠᴇ ᴀ ᴅᴇᴀᴄᴛɪᴠᴀᴛᴇᴅ ᴀᴄᴄᴏᴜɴᴛ).")
    except Exception as e:
        await message.reply_text(f"🎋 ᴀɴ ᴜɴᴇxᴘᴇᴄᴛᴇᴅ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ ᴡʜɪʟᴇ ᴛʀʏɪɴɢ ᴛᴏ ɴᴏᴛɪғʏ ᴛʜᴇ ᴜsᴇʀ: {e}")


#========================================================================#

@Client.on_message(filters.command('premium_users') & filters.private)
async def premium_users_command(client: Bot, message: Message):
    # Check if user is owner or admin
    if message.from_user.id != config.OWNER_ID and message.from_user.id not in config.ADMINS:
        await message.reply_text("❌ ᴏɴʟʏ ᴏᴡɴᴇʀ ᴀɴᴅ ᴀᴅᴍɪɴs ᴄᴀɴ ᴜsᴇ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ.")
        return

    pro_user_docs = await client.mongodb.get_pros_list()
    
    active_users = []
    expired_user_ids_to_remove = []
    now_utc = datetime.now(timezone.utc)

    for user_doc in pro_user_docs:
        expires_at = user_doc.get('expires_at')
        if expires_at and isinstance(expires_at, datetime):
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            
            if expires_at < now_utc:
                expired_user_ids_to_remove.append(user_doc['_id'])
                continue
        
        active_users.append(user_doc)

    cleanup_notice = ""
    if expired_user_ids_to_remove:
        client.LOGGER(__name__, "PREMIUM_USERS_CMD").info(f"Found {len(expired_user_ids_to_remove)} expired users. Cleaning up now...")
        for user_id in expired_user_ids_to_remove:
            await client.mongodb.remove_pro(user_id)
        cleanup_notice = f"🥂 (ᴄʟᴇᴀɴᴇᴅ ᴜᴘ {len(expired_user_ids_to_remove)} ᴇxᴘɪʀᴇᴅ ᴜsᴇʀs.)\n\n"

    if not active_users:
        return await message.reply_text(f"{cleanup_notice}☔ ɴᴏ ᴀᴄᴛɪᴠᴇ ᴘʀᴇᴍɪᴜᴍ ᴜsᴇʀs ғᴏᴜɴᴅ.")

    formatted_users = []
    for user_doc in active_users:
        user_id = user_doc['_id']
        expires_at = user_doc.get('expires_at')
        expiry_text = "🍥 sᴛᴀᴛᴜs: ᴘᴇʀᴍᴀɴᴇɴᴛ"
        if expires_at and isinstance(expires_at, datetime):
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            ist_expires_at = expires_at.astimezone(IST)
            expiry_text = f"⛱️ ᴇxᴘɪʀᴇs: {ist_expires_at.strftime('%ᴅ %ʙ %ʏ, %ʜ:%ᴍ %ᴢ')}"

        try:
            user = await client.get_users(user_id)
            full_name = user.first_name + (" " + user.last_name if user.last_name else "")
            username = f"@{user.username}" if user.username else "ɴ/ᴀ"
            formatted_users.append(
                f"🎩 {full_name}\n"
                f"   🎋 ɪᴅ: <code>{user.id}</code>\n"
                f"   🍷 ᴜsᴇʀɴᴀᴍᴇ: {username}\n"
                f"   {expiry_text}"
            )
        except Exception:
            formatted_users.append(
                f"🎩 ᴜsᴇʀ ɪᴅ: <code>{user_id}</code> (ɪɴғᴏ ɴᴏᴛ ғᴇᴛᴄʜᴀʙʟᴇ)\n"
                f"   {expiry_text}"
            )

    response_text = f"{cleanup_notice}🌀 ᴘʀᴇᴍɪᴜᴍ ᴜsᴇʀs ʟɪsᴛ:\n\n" + "\n\n".join(formatted_users)
    for chunk in [response_text[i:i + 4096] for i in range(0, len(response_text), 4096)]:
        await message.reply_text(chunk, disable_web_page_preview=True)
