# @NaapaExtra

import asyncio
import humanize
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors.pyromod import ListenerTimeout
from pyrogram.errors import FloodWait

# Page 1: Basic Settings
@Client.on_callback_query(filters.regex("^settings$"))
async def settings_panel(client, query):
    # --- Data Loading ---
    saved_settings = await client.mongodb.load_settings(client.session_name)
    if saved_settings:
        client.protect = saved_settings.get("protect", False)
        client.auto_del = saved_settings.get("auto_del", 0)
        client.disable_btn = saved_settings.get("disable_btn", False)
        client.admins = saved_settings.get("admins", [client.owner])
        client.fsub = saved_settings.get("fsub", [])
        client.short_url = saved_settings.get("short_url", "")
        client.short_api = saved_settings.get("short_api", "")
        client.verify_expire = saved_settings.get("verify_expire", 43200)
        if "messages" in saved_settings:
            client.messages.update(saved_settings["messages"])

    # --- Status String Formatting ---
    status_protect = "✅ enabled" if client.protect else "❌ disabled"
    status_share_button = "✅ enabled" if not client.disable_btn else "❌ disabled"
    auto_del_status = f"{client.auto_del}s" if client.auto_del > 0 else "❌ disabled"
    verify_expire_status = f"{humanize.naturaldelta(client.verify_expire)}" if client.verify_expire > 0 else "❌ disabled"

    # --- UI Message ---
    msg = f"""╭───「 🎩 **ʙᴏᴛ ᴄᴏɴꜰɪɢᴜʀᴀᴛɪᴏɴ** 」───╮
│
├─ 🛡️  **ᴄᴏɴᴛᴇɴᴛ ᴘʀᴏᴛᴇᴄᴛɪᴏɴ:** `{status_protect}`
├─ 🔄  **ꜱʜᴀʀᴇ ʙᴜᴛᴛᴏɴ:** `{status_share_button}`
├─ ⏰  **ᴀᴜᴛᴏ-ᴅᴇʟᴇᴛᴇ ꜰɪʟᴇꜱ:** `{auto_del_status}`
├─ ⏳  **ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ ᴛɪᴍᴇ:** `{verify_expire_status}`
│
╰───「 📄 **ᴘᴀɢᴇ 1/2** 」───╯"""

    # --- Keyboard Layout ---
    reply_markup = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton('🛡️ ᴘʀᴏᴛᴇᴄᴛ', callback_data='protect'),
                InlineKeyboardButton('⏰ ᴀᴜᴛᴏ-ᴅᴇʟᴇᴛᴇ', callback_data='auto_del')
            ],
            [
                InlineKeyboardButton('⏳ ᴠᴇʀɪꜰʏ ᴛɪᴍᴇ', callback_data='verify_expire'),
                InlineKeyboardButton('🔄 ꜱʜᴀʀᴇ ʙᴜᴛᴛᴏɴ', callback_data='disable_btn_toggle')
            ],
            [
                InlineKeyboardButton('💰 ꜱʜᴏʀᴛᴇɴᴇʀ', callback_data='shortner_settings'),
                InlineKeyboardButton('📢 ꜰᴏʀᴄᴇ ꜱᴜʙ', callback_data='fsub')
            ],
            [
                InlineKeyboardButton('👑 ᴀᴅᴍɪɴꜱ', callback_data='admins'),
                InlineKeyboardButton('🎨 ᴄᴏɴᴛᴇɴᴛ', callback_data='settings_page2')
            ],
            [
                InlineKeyboardButton('🏠 ʜᴏᴍᴇ', callback_data='home')
            ]
        ]
    )
    
    await query.message.edit_text(msg, reply_markup=reply_markup)

# Page 2: Content & Advanced Settings
@Client.on_callback_query(filters.regex("^settings_page2$"))
async def settings_page2(client, query):
    # --- Force-Sub Channel List Formatting ---
    fsub_channels_text = []
    if client.fsub:
        for ch_id, req_mode, timer in client.fsub:
            try:
                chat = await client.get_chat(ch_id)
                fsub_channels_text.append(f"│  › {chat.title} (<code>{ch_id}</code>)")
            except Exception:
                fsub_channels_text.append(f"│  › <i>ɪɴᴠᴀʟɪᴅ ᴄʜᴀɴɴᴇʟ</i> (<code>{ch_id}</code>)")
    fsub_details = "\n".join(fsub_channels_text) if fsub_channels_text else "│  › ɴᴏ ᴄʜᴀɴɴᴇʟꜱ ᴄᴏɴꜰɪɢᴜʀᴇᴅ"

    shortener_status = "✅ enabled" if client.short_url and client.short_api else "❌ disabled"

    # --- UI Message ---
    msg = f"""╭───「 🎨 **ᴄᴏɴᴛᴇɴᴛ & ᴀᴅᴠᴀɴᴄᴇᴅ** 」───╮
│
├─ 💰  **ꜱʜᴏʀᴛᴇɴᴇʀ:** `{shortener_status}`
├─ 👑  **ᴀᴅᴍɪɴꜱ:** `{len(client.admins)} ᴜꜱᴇʀ(ꜱ)`
│
╭───「 📢 **ꜰᴏʀᴄᴇ ꜱᴜʙꜱᴄʀɪʙᴇ** 」───╮
│
{fsub_details}
│
╰───「 📄 **ᴘᴀɢᴇ 2/2** 」───╯"""

    # --- Keyboard Layout ---
    reply_markup = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton('📝 ᴛᴇxᴛꜱ', callback_data='texts'),
                InlineKeyboardButton('🖼️ ᴘʜᴏᴛᴏꜱ', callback_data='photos')
            ],
            [
                InlineKeyboardButton('« ʙᴀᴄᴋ ᴛᴏ ᴘᴀɢᴇ 1', callback_data='settings')
            ],
            [
                InlineKeyboardButton('🏠 ʜᴏᴍᴇ', callback_data='home')
            ]
        ]
    )
    
    await query.message.edit_text(msg, reply_markup=reply_markup)

# --- All callback handlers below remain unchanged ---
@Client.on_callback_query(filters.regex("^protect$"))
async def protect_callback(client, query):
    client.protect = not client.protect
    await client.mongodb.save_settings(client.session_name, client.get_current_settings())
    await query.answer(f"🛡️ ᴘʀᴏᴛᴇᴄᴛ ᴄᴏɴᴛᴇɴᴛ ɪꜱ ɴᴏᴡ {'ᴇɴᴀʙʟᴇᴅ' if client.protect else 'ᴅɪꜱᴀʙʟᴇᴅ'}", show_alert=True)
    await settings_panel(client, query)

@Client.on_callback_query(filters.regex("^disable_btn_toggle$"))
async def disable_btn_callback(client, query):
    client.disable_btn = not client.disable_btn
    await client.mongodb.save_settings(client.session_name, client.get_current_settings())
    await query.answer(f"🔄 ꜱʜᴀʀᴇ ʙᴜᴛᴛᴏɴ ɪꜱ ɴᴏᴡ {'ᴅɪꜱᴀʙʟᴇᴅ' if client.disable_btn else 'ᴇɴᴀʙʟᴇᴅ'}", show_alert=True)
    await settings_panel(client, query)

@Client.on_callback_query(filters.regex("^auto_del$"))
async def auto_del_callback(client, query):
    await query.answer()
    try:
        current_timer_display = f"{client.auto_del} seconds" if client.auto_del > 0 else "disabled"
        ask_msg = await client.ask(
            chat_id=query.from_user.id,
            text=f"⏰ **ᴄᴜʀʀᴇɴᴛ ᴀᴜᴛᴏ-ᴅᴇʟᴇᴛᴇ ᴛɪᴍᴇʀ:** `{current_timer_display}`\n\n📥 ᴇɴᴛᴇʀ ɴᴇᴡ ᴛɪᴍᴇ ɪɴ ꜱᴇᴄᴏɴᴅꜱ (ᴜꜱᴇ 0 ᴛᴏ ᴅɪꜱᴀʙʟᴇ):",
            filters=filters.text, timeout=60
        )
        if ask_msg.text.isdigit():
            client.auto_del = int(ask_msg.text)
            await client.mongodb.save_settings(client.session_name, client.get_current_settings())
            new_timer_display = f"{client.auto_del} seconds" if client.auto_del > 0 else "disabled"
            await ask_msg.reply(f"✅ ᴀᴜᴛᴏ-ᴅᴇʟᴇᴛᴇ ᴛɪᴍᴇʀ ᴜᴘᴅᴀᴛᴇᴅ ᴛᴏ `{new_timer_display}`")
        else:
            await ask_msg.reply("❌ ɪɴᴠᴀʟɪᴅ ɪɴᴘᴜᴛ. ᴘʟᴇᴀꜱᴇ ᴇɴᴛᴇʀ ᴀ ᴠᴀʟɪᴅ ɴᴜᴍʙᴇʀ")
    except ListenerTimeout:
        await query.message.reply("⏰ ᴛɪᴍᴇᴏᴜᴛ. ᴏᴘᴇʀᴀᴛɪᴏɴ ᴄᴀɴᴄᴇʟʟᴇᴅ")
    
    await settings_panel(client, query)

@Client.on_callback_query(filters.regex("^verify_expire$"))
async def verify_expire_callback(client, query):
    await query.answer()
    try:
        current_timer_display = f"{humanize.naturaldelta(client.verify_expire)}" if client.verify_expire > 0 else "disabled"
        ask_msg = await client.ask(
            chat_id=query.from_user.id,
            text=f"⏳ **ᴄᴜʀʀᴇɴᴛ ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ ᴇxᴘɪʀʏ:** `{current_timer_display}`\n\n📥 ᴇɴᴛᴇʀ ɴᴇᴡ ᴛɪᴍᴇ ɪɴ ꜱᴇᴄᴏɴᴅꜱ (ᴇ.ɢ., `3600` ꜰᴏʀ 1 ʜᴏᴜʀ):",
            filters=filters.text, timeout=60
        )
        if ask_msg.text.isdigit():
            client.verify_expire = int(ask_msg.text)
            await client.mongodb.save_settings(client.session_name, client.get_current_settings())
            new_timer_display = f"{humanize.naturaldelta(client.verify_expire)}" if client.verify_expire > 0 else "disabled"
            await ask_msg.reply(f"✅ ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ ᴇxᴘɪʀʏ ᴛɪᴍᴇ ᴜᴘᴅᴀᴛᴇᴅ ᴛᴏ `{new_timer_display}`")
        else:
            await ask_msg.reply("❌ ɪɴᴠᴀʟɪᴅ ɪɴᴘᴜᴛ. ᴘʟᴇᴀꜱᴇ ᴇɴᴛᴇʀ ᴀ ᴠᴀʟɪᴅ ɴᴜᴍʙᴇʀ ᴏꜰ ꜱᴇᴄᴏɴᴅꜱ")
    except ListenerTimeout:
        await query.message.reply("⏰ ᴛɪᴍᴇᴏᴜᴛ. ᴏᴘᴇʀᴀᴛɪᴏɴ ᴄᴀɴᴄᴇʟʟᴇᴅ")
    
    await settings_panel(client, query)
