# @NaapaExtra
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors.pyromod import ListenerTimeout

@Client.on_callback_query(filters.regex("^photos$"))
async def photos_panel(client: Client, query: CallbackQuery):
    await query.answer()
    
    def get_photo(key):
        return client.messages.get(key) or "<i>(Not Set)</i>"

    # --- NEW AND IMPROVED UI ---
    msg = f"""╭───「 🖼️ **Photo Customization** 」
│
├─ 🖼️ **Start Photo:**
│  <code>{get_photo('START_PHOTO')}</code>
├─ 📢 **FSub Photo:**
│  <code>{get_photo('FSUB_PHOTO')}</code>
└─ ⏳ **Verify Photo:**
   <code>{get_photo('VERIFY_PHOTO')}</code>

╰────────────────────

*You must provide a valid `graph.org` or `telegra.ph` link. Click a button below to edit a photo link.*"""
    
    reply_markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton('🖼️ Start', callback_data='setphoto_START_PHOTO'),
            InlineKeyboardButton('📢 FSub', callback_data='setphoto_FSUB_PHOTO'),
            InlineKeyboardButton('⏳ Verify', callback_data='setphoto_VERIFY_PHOTO')
        ],
        [
            InlineKeyboardButton('◂ Back to Settings', callback_data='settings')
        ]
    ])
    
    await query.message.edit_text(msg, reply_markup=reply_markup)

@Client.on_callback_query(filters.regex("^setphoto_"))
async def set_photo(client: Client, query: CallbackQuery):
    await query.answer()
    
    photo_key = query.data.split("_", 1)[1]
    
    key_name_map = {
        "START_PHOTO": "Start Photo",
        "FSUB_PHOTO": "Force Subscribe Photo",
        "VERIFY_PHOTO": "Verification Photo"
    }
    
    try:
        ask_msg = await client.ask(
            chat_id=query.from_user.id,
            text=f"Please send the new **graph.org** or **telegra.ph** link for **{key_name_map.get(photo_key, photo_key)}**.\n\nDirect photo uploads are not supported.\n\nType `remove` to clear the current photo or `cancel` to go back.",
            filters=filters.photo | filters.text,
            timeout=60
        )

        if ask_msg.text:
            text = ask_msg.text.lower()
            if text == 'cancel':
                await ask_msg.reply("Operation cancelled.")
            elif text == 'remove':
                client.messages[photo_key] = ""
                await client.mongodb.save_settings(client.session_name, client.get_current_settings())
                await ask_msg.reply(f"✅ Photo for `{key_name_map.get(photo_key, photo_key)}` has been removed.")
            else:
                url = ask_msg.text.strip()
                if url.startswith("https://graph.org/") or url.startswith("https://telegra.ph/"):
                    client.messages[photo_key] = url
                    await client.mongodb.save_settings(client.session_name, client.get_current_settings())
                    await ask_msg.reply(f"✅ Photo for `{key_name_map.get(photo_key, photo_key)}` updated from valid URL!")
                else:
                    await ask_msg.reply("❌ **Invalid URL.** Please only provide a link starting with `https://graph.org/` or `https://telegra.ph/`.")
        
        elif ask_msg.photo:
            await ask_msg.reply("❌ **Error: Direct photo uploads are not allowed.** Please upload your image to [graph.org](https://graph.org) and send me the resulting link.", disable_web_page_preview=True)

    except ListenerTimeout:
        await query.message.reply("⏰ Timeout. Operation cancelled.")
    except Exception as e:
        await query.message.reply(f"An error occurred: {e}")

    await photos_panel(client, query) # Go back to the refined panel
