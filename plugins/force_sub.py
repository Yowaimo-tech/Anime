# @NaapaExtra

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from helper.helper_func import is_bot_admin

@Client.on_callback_query(filters.regex("^fsub$"))
async def fsub_panel(client: Client, query: CallbackQuery):
    await query.answer()

    # --- UI Formatting (MODIFIED) ---
    channel_list_text = []
    if client.fsub:
        for ch_id, req_mode, timer in client.fsub:
            try:
                chat = await client.get_chat(ch_id)
                mode_indicator = " (Request Mode)" if req_mode else ""
                # This line is now updated to include the channel ID
                channel_list_text.append(f"│  › {chat.title} (<code>{ch_id}</code>){mode_indicator}")
            except Exception:
                channel_list_text.append(f"│  › <i>Invalid Channel</i> (<code>{ch_id}</code>)")
    
    fsub_details = "\n".join(channel_list_text) if channel_list_text else "│  › No channels have been added yet."

    msg = f"""╭───「 📢 **Force Subscribe** 」
│
{fsub_details}
│
╰────────────────────

*Manage the channels users must join to use the bot. Use the buttons below to add or remove channels.*"""

    reply_markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton('➕ Add Channel', callback_data='add_fsub'),
            InlineKeyboardButton('➖ Remove Channel', callback_data='rm_fsub')
        ],
        [
            InlineKeyboardButton('◂ Back to Settings', callback_data='settings')
        ]
    ])
    
    await query.message.edit_text(msg, reply_markup=reply_markup)

@Client.on_callback_query(filters.regex('^add_fsub$'))
async def add_fsub_channel(client: Client, query: CallbackQuery):
    await query.answer()
    try:
        ask_msg = await client.ask(
            query.from_user.id,
            "**Send channel details in this format:**\n`channel_id request_mode timer`\n\n"
            "• `channel_id`: The ID of the channel (e.g., `-100123...`).\n"
            "• `request_mode`: `true` or `false` (if users must request to join).\n"
            "• `timer`: Link expiry in minutes (use `0` for permanent).\n\n"
            "**Example:** `-10012345 true 5`",
            filters=filters.text, timeout=120
        )
        parts = ask_msg.text.split()
        if len(parts) != 3:
            return await ask_msg.reply("❌ Invalid format. Please provide all three parts and try again.")

        channel_id = int(parts[0])
        request_mode = parts[1].lower() == 'true'
        timer = int(parts[2])

        if any(ch[0] == channel_id for ch in client.fsub):
            return await ask_msg.reply("This channel is already in the list.")

        is_admin, error_msg = await is_bot_admin(client, channel_id)
        if not is_admin:
            return await ask_msg.reply(f"❌ **Error:** {error_msg}\n\nPlease make me an admin in the channel with 'Invite Users' permission and try again.")

        client.fsub.append([channel_id, request_mode, timer])
        await client.mongodb.save_settings(client.session_name, client.get_current_settings())
        await ask_msg.reply("✅ Channel added successfully.")
    except Exception as e:
        await query.message.reply(f"An error occurred: {e}")
    
    await fsub_panel(client, query)

@Client.on_callback_query(filters.regex('^rm_fsub$'))
async def rm_fsub_channel(client: Client, query: CallbackQuery):
    await query.answer()
    try:
        ask_msg = await client.ask(query.from_user.id, "Send the Channel ID to remove.", filters=filters.text, timeout=60)
        channel_id_to_remove = int(ask_msg.text)
        
        initial_len = len(client.fsub)
        client.fsub = [ch for ch in client.fsub if ch[0] != channel_id_to_remove]
        
        if len(client.fsub) < initial_len:
            await client.mongodb.save_settings(client.session_name, client.get_current_settings())
            await ask_msg.reply("🗑️ Channel removed successfully.")
        else:
            await ask_msg.reply("Channel not found in the list.")
    except Exception as e:
        await query.message.reply(f"An error occurred: {e}")
        
    await fsub_panel(client, query)
