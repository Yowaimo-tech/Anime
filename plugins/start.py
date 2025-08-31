# File: plugins/start.py

from helper.helper_func import *
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import humanize
import time
import secrets
import random
import string as rohit_string
from datetime import datetime
from zoneinfo import ZoneInfo
from plugins.shortner import get_short
import config

IST = ZoneInfo("Asia/Kolkata")
CACHE_TTL_SECONDS = 300

@Client.on_message(filters.command('start') & filters.private)
@force_sub
async def start_command(client: Client, message: Message):
    user_id = message.from_user.id
    
    user_state, _ = await client.mongodb.get_user_state(user_id)
    if user_state is None: return await message.reply("A critical database error occurred.")
    if user_state.get('banned', False): return await message.reply("**You have been banned from using this bot!**")

    if len(message.command) > 1:
        payload = message.command[1]

        if payload.startswith("verify_"):
            token = payload.split("_", 1)[1]
            verify_status = await client.mongodb.get_verify_status(user_id)
            
            if verify_status.get('verify_token') != token:
                return await message.reply("⚠️ **Link Expired or Invalid.**\nPlease request the file again.")

            verify_status['is_verified'] = True
            verify_status['verified_time'] = time.time()
            verify_status['verify_token'] = ""
            await client.mongodb.update_verify_status(user_id, verify_status)
            await client.mongodb.increment_verify_count()
            
            file_payload = verify_status.get('file_payload')
            buttons = [[InlineKeyboardButton("✖️ ᴄʟᴏꜱᴇ", callback_data="close")]]
            if file_payload:
                buttons.insert(0, [InlineKeyboardButton("✅ ɢᴇᴛ ʏᴏᴜʀ ꜰɪʟᴇꜱ", callback_data=f"get_file_{file_payload}")])

            return await message.reply(
                f"✅ **Successfully verified!**\n\nYour access is valid for the next **{client.verify_expire} seconds**.",
                reply_markup=InlineKeyboardMarkup(buttons)
            )

        base64_string = payload
        
        if user_id in client.admins or user_state.get('is_pro', False):
            return await send_files(client, user_id, base64_string)

        verify_status = await client.mongodb.get_verify_status(user_id)
        is_still_verified = verify_status.get('is_verified', False) and (time.time() - verify_status.get('verified_time', 0)) < client.verify_expire

        if is_still_verified:
            return await send_files(client, user_id, base64_string)
        else:
            token = ''.join(random.choices(rohit_string.ascii_letters + rohit_string.digits, k=10))
            
            verify_status['verify_token'] = token
            verify_status['file_payload'] = base64_string
            await client.mongodb.update_verify_status(user_id, verify_status)
            
            link = f"https://t.me/{client.username}?start=verify_{token}"
            short_link = get_short(link, client)

            btn = [[InlineKeyboardButton("• ᴏᴘᴇɴ ʟɪɴᴋ •", url=short_link), InlineKeyboardButton("• ᴛᴜᴛᴏʀɪᴀʟ •", url=config.TUT_VID)],[InlineKeyboardButton("• ʙᴜʏ ᴘʀᴇᴍɪᴜᴍ •", url="https://t.me/Mayhem_Premium_Bot")]]
            verify_photo = client.messages.get("VERIFY_PHOTO", "")
            
            # --- THIS IS THE MODIFIED LINE ---
            caption = f"**‼️ ʏᴏᴜ'ʀᴇ ᴀʀᴇ ɴᴏᴛ ᴠᴇʀɪғɪᴇᴅ ‼️\n\n›› ᴘʟᴇᴀsᴇ ᴠᴇʀɪғʏ ᴀɴᴅ ɢᴇᴛ ᴜɴʟɪᴍɪᴛᴇᴅ ᴀᴄᴄᴇss ғᴏʀ {client.verify_expire} ꜱᴇᴄᴏɴᴅꜱ ✅\n\n›› ɪғ ʏᴏᴜ ᴅᴏɴᴛ ᴡᴀɴᴛ ᴛᴏ ᴏᴘᴇɴ sʜᴏʀᴛ ʟɪɴᴋs ᴛʜᴇɴ ʏᴏᴜ ᴄᴀɴ ᴛᴀᴋᴇ ᴘʀᴇᴍɪᴜᴍ sᴇʀᴠɪᴄᴇs.**"
            
            if verify_photo:
                await message.reply_photo(photo=verify_photo, caption=caption, reply_markup=InlineKeyboardMarkup(btn))
            else:
                await message.reply(text=caption, reply_markup=InlineKeyboardMarkup(btn))
            return
            
    else:
        buttons = [[InlineKeyboardButton("ʜᴇʟᴘ", callback_data="about"), InlineKeyboardButton("ᴄʟᴏꜱᴇ", callback_data='close')]]
        if user_id in client.admins:
            buttons.insert(0, [InlineKeyboardButton("⛩️ ꜱᴇᴛᴛɪɴɢꜱ ⛩️", callback_data="settings")])
        photo = client.messages.get("START_PHOTO", "")
        start_caption = client.messages.get('START', 'Welcome!').format(
            first=message.from_user.first_name, last=message.from_user.last_name, 
            username=f"@{message.from_user.username}" if message.from_user.username else "N/A", 
            mention=message.from_user.mention, id=user_id
        )
        try:
            if photo: await message.reply_photo(photo=photo, caption=start_caption, reply_markup=InlineKeyboardMarkup(buttons))
            else: await message.reply_text(text=start_caption, reply_markup=InlineKeyboardMarkup(buttons))
        except Exception as e: client.LOGGER(__name__, "WELCOME").error(f"Error sending welcome to {user_id}: {e}")

@Client.on_callback_query(filters.regex(r"^get_file_"))
async def get_file_callback_handler(client: Client, query: CallbackQuery):
    base64_string = query.data.split("_", 2)[2]
    await query.answer("Please wait, sending your file(s)...", show_alert=True)
    await send_files(client, query.from_user.id, base64_string)
    await query.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✖️ ᴅᴏɴᴇ", callback_data="close")]]))

async def get_user_state_with_cache(client: Client, user_id: int):
    now = time.time()
    state, pro_expires_at = await client.mongodb.get_user_state(user_id)
    if state is not None:
        client.user_cache[user_id] = {'state': state, 'timestamp': now, 'pro_expires_at': pro_expires_at}
    return state

@Client.on_message(filters.command('request') & filters.private)
async def request_command(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id in client.admins or user_id == client.owner: return await message.reply_text("🔹 **Admins cannot make requests.**")
    user_state = await get_user_state_with_cache(client, user_id)
    if user_state is None or not user_state.get('is_pro', False): return await message.reply("❌ **Only premium users can make requests.**", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("ʙᴜʏ ᴘʀᴇᴍɪᴜᴍ •", url="https://t.me/NaapaExtra")]]))
    if len(message.command) < 2: return await message.reply("⚠️ **Usage:**\n`/request <content name>`")
    owner_message = f"📩 **New Request**\n\n**From:** {message.from_user.mention} (`{user_id}`)\n**Request:** `{' '.join(message.command[1:])}`"
    try:
        await client.send_message(client.owner, owner_message)
        await message.reply("✅ **Your request has been sent!**")
    except Exception as e:
        client.LOGGER(__name__, "REQUEST").error(f"Could not forward request from {user_id}: {e}")
        await message.reply("Sorry, there was an error sending your request.")

@Client.on_message(filters.command('profile') & filters.private)
async def my_plan(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id in client.admins or user_id == client.owner: return await message.reply_text("🔹 **You're an admin. You have access to everything!**")
    user_state = await get_user_state_with_cache(client, user_id)
    if user_state is None: return await message.reply("Could not fetch profile due to a database error.")
    if user_state.get('is_pro', False):
        pro_data = await client.mongodb.get_pro_user(user_id)
        expires_at = pro_data.get('expires_at') if pro_data else None
        if expires_at and isinstance(expires_at, datetime):
            if expires_at.tzinfo is None: expires_at = expires_at.replace(tzinfo=timezone.utc)
            expiry_text = f"🔸 **Expires in:** {humanize.naturaldelta(expires_at - datetime.now(timezone.utc))}"
        else: expiry_text = "🔸 **Expiry:** Permanent"
        plan_text = f"**👤 Your Profile:**\n\n🔸 **Plan:** `Premium`\n{expiry_text}\n🔸 **Ads:** `Disabled`\n🔸 **Requests:** `Enabled`"
    else:
        plan_text = "**👤 Your Profile:**\n\n🔸 **Plan:** `Free`\n🔸 **Ads:** `Enabled`\n🔸 **Requests:** `Disabled`\n\n🔓 Unlock Premium to get more benefits\nContact: @Mayhem_Premium_Bot"
    await message.reply_text(plan_text)
