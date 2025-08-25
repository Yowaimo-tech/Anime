# @NaapaExtra

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.errors.pyromod import ListenerTimeout

# Main texts settings panel with the refined UI
@Client.on_callback_query(filters.regex("^texts$"))
async def texts_panel(client: Client, query: CallbackQuery):
    await query.answer()
    
    def get_text(key):
        return client.messages.get(key) or "<i>(Not Set)</i>"

    # --- THIS IS THE CORRECTED MESSAGE FORMATTING ---
    # The 'FSUB' get_text call is now correctly inside the blockquote
    msg = f"""╭───「 📝 **Text Customization** 」
│
├─ 💬 **Start Text**
│  <blockquote>{get_text('START')}</blockquote>
├─ 📢 **Force Subscribe Text**
│  <blockquote>{get_text('FSUB')}</blockquote>
├─ ℹ️ **About Text**
│  <blockquote>{get_text('ABOUT')}</blockquote>
└─ 🚫 **Unauthorized User Text**
   <blockquote>{get_text('REPLY')}</blockquote>

╰────────────────────

*Click a button below to edit a message.*"""
    
    # Updated keyboard with emojis for consistency
    reply_markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton('💬 Start', callback_data='settext_START'),
            InlineKeyboardButton('📢 FSub', callback_data='settext_FSUB')
        ],
        [
            InlineKeyboardButton('ℹ️ About', callback_data='settext_ABOUT'),
            InlineKeyboardButton('🚫 Unauthorized', callback_data='settext_REPLY')
        ],
        [
            InlineKeyboardButton('◂ Back to Settings', callback_data='settings')
        ]
    ])
    
    await query.message.edit_text(msg, reply_markup=reply_markup)

# Generic handler for all text setting buttons (logic remains the same)
@Client.on_callback_query(filters.regex("^settext_"))
async def set_text(client: Client, query: CallbackQuery):
    await query.answer()
    
    text_key = query.data.split("_", 1)[1]
    
    key_name_map = {
        "START": "Start Text",
        "FSUB": "Force Subscribe Text",
        "ABOUT": "About Text",
        "REPLY": "Unauthorized User Text"
    }
    
    try:
        ask_msg = await client.ask(
            chat_id=query.from_user.id,
            text=f"Please send the new text for **{key_name_map.get(text_key, text_key)}**.\n\nHTML and Markdown formatting are supported.\n\nType `cancel` to go back.",
            filters=filters.text,
            timeout=120
        )

        if ask_msg.text.lower() == 'cancel':
            await ask_msg.reply("Operation cancelled.")
        else:
            client.messages[text_key] = ask_msg.text
            await client.mongodb.save_settings(client.session_name, client.get_current_settings())
            await ask_msg.reply(f"✅ Text for `{key_name_map.get(text_key, text_key)}` has been updated and saved!")

    except ListenerTimeout:
        await query.message.reply("⏰ Timeout. Operation cancelled.")
    except Exception as e:
        await query.message.reply(f"An error occurred: {e}")

    await texts_panel(client, query)
