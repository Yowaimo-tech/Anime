# @NaapaExtra

import asyncio
import humanize
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors.pyromod import ListenerTimeout
from pyrogram.errors import FloodWait

@Client.on_callback_query(filters.regex("^settings$"))
async def settings_panel(client, query):
    # --- Data Loading (No Changes Here) ---
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

    # --- Force-Sub Channel List Formatting (MODIFIED) ---
    fsub_channels_text = []
    if client.fsub:
        for ch_id, req_mode, timer in client.fsub:
            try:
                chat = await client.get_chat(ch_id)
                # This line is now updated to include the channel ID
                fsub_channels_text.append(f"│  › {chat.title} (<code>{ch_id}</code>)")
            except Exception:
                fsub_channels_text.append(f"│  › <i>Invalid Channel</i> (<code>{ch_id}</code>)")
    fsub_details = "\n".join(fsub_channels_text) if fsub_channels_text else "│  › No channels configured."

    # --- Status String Formatting (No Changes Here) ---
    status_protect = "✅ Enabled" if client.protect else "❌ Disabled"
    status_share_button = "✅ Enabled" if not client.disable_btn else "❌ Disabled"
    auto_del_status = f"{client.auto_del}s" if client.auto_del > 0 else "❌ Disabled"
    shortener_status = "✅ Enabled" if client.short_url and client.short_api else "❌ Disabled"
    verify_expire_status = f"{client.verify_expire}s" if client.verify_expire > 0 else "❌ Disabled"

    # --- UI Message (No Changes Here) ---
    msg = f"""╭───「 ⚙️ **Bot Configuration** 」
│
├─ 🛡️ **Protect Content:** <code>{status_protect}</code>
├─ 🔄 **Share Button:** <code>{status_share_button}</code>
├─ ⏰ **Auto-Delete Files:** <code>{auto_del_status}</code>
└─ ⏳ **Verification Time:** <code>{verify_expire_status}</code>

╭───「  monetiz. & Users 」
│
├─ 💰 **Shortener:** <code>{shortener_status}</code>
└─ 👑 **Admins:** <code>{len(client.admins)} User(s)</code>

╭───「 📢 **Force Subscribe** 」
│
{fsub_details}
│
╰─────────────────"""

    # --- Keyboard Layout (No Changes Here) ---
    reply_markup = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton('🛡️ Protect', callback_data='protect'),
                InlineKeyboardButton('⏰ Auto-Delete', callback_data='auto_del')
            ],
            [
                InlineKeyboardButton('⏳ Verify Time', callback_data='verify_expire'),
                InlineKeyboardButton('🔄 Share Button', callback_data='disable_btn_toggle')
            ],
            [
                InlineKeyboardButton('👑 Admins', callback_data='admins'),
                InlineKeyboardButton('🔗 Force Sub', callback_data='fsub')
            ],
            [
                InlineKeyboardButton('📝 Texts', callback_data='texts'),
                InlineKeyboardButton('🖼️ Photos', callback_data='photos')
            ],
            [
                InlineKeyboardButton('💰 Shortener Settings', callback_data='shortner_settings')
            ],
            [
                InlineKeyboardButton('« Back to Home', callback_data='home')
            ]
        ]
    )
    
    await query.message.edit_text(msg, reply_markup=reply_markup)

# --- All callback handlers below remain unchanged ---
@Client.on_callback_query(filters.regex("^protect$"))
async def protect_callback(client, query):
    client.protect = not client.protect
    await client.mongodb.save_settings(client.session_name, client.get_current_settings())
    await query.answer(f"Protect Content is now {'Enabled' if client.protect else 'Disabled'}", show_alert=True)
    await settings_panel(client, query)

@Client.on_callback_query(filters.regex("^disable_btn_toggle$"))
async def disable_btn_callback(client, query):
    client.disable_btn = not client.disable_btn
    await client.mongodb.save_settings(client.session_name, client.get_current_settings())
    await query.answer(f"Share Button is now {'Disabled' if client.disable_btn else 'Enabled'}", show_alert=True)
    await settings_panel(client, query)

@Client.on_callback_query(filters.regex("^auto_del$"))
async def auto_del_callback(client, query):
    await query.answer()
    try:
        current_timer_display = f"{client.auto_del} seconds" if client.auto_del > 0 else "Disabled"
        ask_msg = await client.ask(
            chat_id=query.from_user.id,
            text=f"Current auto-delete timer is `{current_timer_display}`.\n\nEnter a new time in seconds (use 0 to disable).",
            filters=filters.text, timeout=60
        )
        if ask_msg.text.isdigit():
            client.auto_del = int(ask_msg.text)
            await client.mongodb.save_settings(client.session_name, client.get_current_settings())
            new_timer_display = f"{client.auto_del} seconds" if client.auto_del > 0 else "Disabled"
            await ask_msg.reply(f"✅ Auto-delete timer updated to `{new_timer_display}`.")
        else:
            await ask_msg.reply("❌ Invalid input. Please enter a valid number.")
    except ListenerTimeout:
        await query.message.reply("⏰ Timeout. Operation cancelled.")
    
    await settings_panel(client, query)

@Client.on_callback_query(filters.regex("^verify_expire$"))
async def verify_expire_callback(client, query):
    await query.answer()
    try:
        current_timer_display = f"{client.verify_expire} seconds" if client.verify_expire > 0 else "Disabled"
        ask_msg = await client.ask(
            chat_id=query.from_user.id,
            text=f"Current verification expiry time is `{current_timer_display}`.\n\nEnter a new time in seconds (e.g., `3600` for 1 hour). Use 0 to disable.",
            filters=filters.text, timeout=60
        )
        if ask_msg.text.isdigit():
            client.verify_expire = int(ask_msg.text)
            await client.mongodb.save_settings(client.session_name, client.get_current_settings())
            new_timer_display = f"{client.verify_expire} seconds" if client.verify_expire > 0 else "Disabled"
            await ask_msg.reply(f"✅ Verification expiry time updated to `{new_timer_display}`.")
        else:
            await ask_msg.reply("❌ Invalid input. Please enter a valid number of seconds.")
    except ListenerTimeout:
        await query.message.reply("⏰ Timeout. Operation cancelled.")
    
    await settings_panel(client, query)
