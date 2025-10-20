import asyncio
import base64
from bot import Bot
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, InputMediaPhoto
from pyrogram.errors import UserNotParticipant, FloodWait, ChatAdminRequired, RPCError
from pyrogram.errors import InviteHashExpired, InviteRequestSent
from helper.database import MongoDB
from config import *
from helper.database import *
from datetime import datetime, timedelta

PAGE_SIZE = 6
chat_info_cache = {}

# Default photo for links (you can change this URL)
DEFAULT_LINKS_PHOTO = "https://i.ibb.co/20xbCXvP/jsorg.jpg"

async def revoke_invite_after_5_minutes(client: Client, channel_id: int, link: str, is_request: bool = False):
    """Revoke invite link after 10 minutes"""
    await asyncio.sleep(600)  # 10 minutes
    try:
        await client.revoke_chat_invite_link(channel_id, link)
        action_type = "join request" if is_request else "invite"
        print(f"{action_type.capitalize()} link revoked for channel {channel_id}")
    except Exception as e:
        print(f"Failed to revoke {action_type} link for channel {channel_id}: {e}")

async def validate_chat_permissions(client: Client, chat) -> bool:
    """Validate if bot has necessary permissions in the chat"""
    if not chat.permissions:
        return True
        
    # Check for posting/editing permissions
    if hasattr(chat.permissions, 'can_post_messages') and chat.permissions.can_post_messages:
        return True
    if hasattr(chat.permissions, 'can_edit_messages') and chat.permissions.can_edit_messages:
        return True
        
    # For groups, check if bot is admin
    if chat.type.name in ['GROUP', 'SUPERGROUP']:
        try:
            bot_member = await client.get_chat_member(chat.id, (await client.get_me()).id)
            return bot_member.status.name in ['ADMINISTRATOR', 'CREATOR']
        except Exception:
            return False
            
    return False

async def generate_channel_links(client: Client, channel_id: int) -> tuple:
    """Generate both normal and request links for a channel"""
    base64_invite = await save_encoded_link(channel_id)
    normal_link = f"https://t.me/{client.username}?start={base64_invite}"
    
    base64_request = await encode(str(channel_id))
    await save_encoded_link2(channel_id, base64_request)
    request_link = f"https://t.me/{client.username}?start=req_{base64_request}"
    
    return normal_link, request_link

@Client.on_message((filters.command('addchat') | filters.command('addch')) & filters.private)
async def set_channel(client: Client, message: Message):
    """Add a chat to the database - Only for admins"""
    # Check if user is admin
    if message.from_user.id not in ADMINS:
        return await message.reply("<b>🚫 Access Denied. This command is for admins only.</b>")
    
    if len(message.command) < 2:
        return await message.reply(
            "<b><blockquote expandable>Invalid chat ID. Example: <code>/addchat &lt;chat_id&gt;</code></b>"
        )
    
    try:
        channel_id = int(message.command[1])
    except ValueError:
        return await message.reply("<b><blockquote expandable>Invalid chat ID format. Must be a number.</b>")
    
    try:
        chat = await client.get_chat(channel_id)
        
        if not await validate_chat_permissions(client, chat):
            return await message.reply(
                f"<b><blockquote expandable>I am in {chat.title}, but I lack posting or editing permissions.</b>"
            )
        
        await save_channel(channel_id)
        normal_link, request_link = await generate_channel_links(client, channel_id)
        
        reply_text = (
            f"<b><blockquote expandable>✅ Chat {chat.title} ({channel_id}) has been added successfully.</b>\n\n"
            f"<b>🔗 Normal Link:</b> <code>{normal_link}</code>\n"
            f"<b>🔗 Request Link:</b> <code>{request_link}</code>"
        )
        return await message.reply(reply_text)
    
    except UserNotParticipant:
        return await message.reply(
            "<b><blockquote expandable>I am not a member of this channel. Please add me and try again.</b>"
        )
    except FloodWait as e:
        await asyncio.sleep(e.x)
        return await set_channel(client, message)
    except RPCError as e:
        return await message.reply(f"<b>RPC Error:</b> <code>{str(e)}</code>")
    except Exception as e:
        return await message.reply(f"<b>Unexpected Error:</b> <code>{str(e)}</code>")

@Client.on_message((filters.command('delchat') | filters.command('delch')) & filters.private)
async def del_channel(client: Client, message: Message):
    """Remove a chat from the database - Only for admins"""
    # Check if user is admin
    if message.from_user.id not in ADMINS:
        return await message.reply("<b>🚫 Access Denied. This command is for admins only.</b>")
    
    if len(message.command) < 2:
        return await message.reply(
            "<b><blockquote expandable>Invalid chat ID. Example: <code>/delch &lt;chat_id&gt;</code></b>"
        )
    
    try:
        channel_id = int(message.command[1])
    except ValueError:
        return await message.reply("<b><blockquote expandable>Invalid chat ID format. Must be a number.</b>")
    
    await delete_channel(channel_id)
    return await message.reply(f"<b><blockquote expandable>❌ Chat {channel_id} has been removed successfully.</b>")

async def send_paginated_content(client, message, channels, page, content_type, status_msg=None, edit=False):
    """Generic function to send paginated content"""
    if status_msg:
        await status_msg.delete()
        
    total_pages = (len(channels) + PAGE_SIZE - 1) // PAGE_SIZE
    start_idx = page * PAGE_SIZE
    end_idx = start_idx + PAGE_SIZE
    
    # Get chat info for current page
    chat_tasks = [get_chat_info(client, channel_id) for channel_id in channels[start_idx:end_idx]]
    
    try:
        chat_infos = await asyncio.gather(*chat_tasks, return_exceptions=True)
    except Exception as e:
        print(f"Error gathering chat info: {e}")
        chat_infos = [None] * len(channels[start_idx:end_idx])
    
    buttons = []
    row = []
    
    for i, chat_info in enumerate(chat_infos):
        channel_id = channels[start_idx + i]
        
        if isinstance(chat_info, Exception) or chat_info is None:
            print(f"Error getting chat info for channel {channel_id}: {chat_info}")
            continue
            
        try:
            if content_type == "channel":
                base64_invite = await save_encoded_link(channel_id)
                button_link = f"https://t.me/{client.username}?start={base64_invite}"
            elif content_type == "request":
                base64_request = await encode(str(channel_id))
                await save_encoded_link2(channel_id, base64_request)
                button_link = f"https://t.me/{client.username}?start=req_{base64_request}"
            else:
                continue
                
            row.append(InlineKeyboardButton(chat_info.title, url=button_link))
            
            if len(row) == 2:
                buttons.append(row)
                row = []
                
        except Exception as e:
            print(f"Error generating link for channel {channel_id}: {e}")
    
    if row:
        buttons.append(row)
    
    # Add navigation buttons
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("◀️ Previous", callback_data=f"{content_type}page_{page-1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("Next ▶️", callback_data=f"{content_type}page_{page+1}"))
    
    if nav_buttons:
        buttons.append(nav_buttons)
    
    reply_markup = InlineKeyboardMarkup(buttons)
    
    titles = {
        "channel": "📺 Select a channel to access:",
        "request": "🔐 Select a channel to request access:"
    }
    
    if edit:
        await message.edit_text(titles.get(content_type, "Select:"), reply_markup=reply_markup)
    else:
        await message.reply(titles.get(content_type, "Select:"), reply_markup=reply_markup)

@Client.on_message(filters.command('ch_links') & filters.private)
async def channel_post(client: Client, message: Message):
    """Show channel links as buttons - Only for admins"""
    # Check if user is admin
    if message.from_user.id not in ADMINS:
        return await message.reply("<b>🚫 Access Denied. This command is for admins only.</b>")
    
    status_msg = await message.reply("⏳")
    try:
        channels = await get_channels()
        if not channels:
            await status_msg.delete()
            return await message.reply(
                "<b><blockquote expandable>No channels available. Please use /addch to add a channel.</b>"
            )
        await send_paginated_content(client, message, channels, 0, "channel", status_msg)
    except Exception as e:
        await status_msg.delete()
        await message.reply(f"<b>Error:</b> <code>{str(e)}</code>")

@Client.on_message(filters.command('reqlink') & filters.private)
async def req_post(client: Client, message: Message):
    """Show request links as buttons - Only for admins"""
    # Check if user is admin
    if message.from_user.id not in ADMINS:
        return await message.reply("<b>🚫 Access Denied. This command is for admins only.</b>")
    
    status_msg = await message.reply("⏳")
    try:
        channels = await get_channels()
        if not channels:
            await status_msg.delete()
            return await message.reply(
                "<b><blockquote expandable>No channels available. Please use /addch to add a channel.</b>"
            )
        await send_paginated_content(client, message, channels, 0, "request", status_msg)
    except Exception as e:
        await status_msg.delete()
        await message.reply(f"<b>Error:</b> <code>{str(e)}</code>")

@Client.on_callback_query(filters.regex(r"(channel|req)page_(\d+)"))
async def paginate_content(client: Client, callback_query):
    """Handle pagination for both channel and request pages"""
    # Check if user is admin
    if callback_query.from_user.id not in ADMINS:
        await callback_query.answer("🚫 Access Denied. Admins only.", show_alert=True)
        return
    
    content_type, page_str = callback_query.data.split("_")
    page = int(page_str)
    
    status_msg = await callback_query.message.edit_text("⏳")
    channels = await get_channels()
    await send_paginated_content(
        client, callback_query.message, channels, page, content_type, status_msg, edit=True
    )

@Client.on_message(filters.command('links') & filters.private)
async def show_links(client: Client, message: Message):
    """Show all links as text with pagination and photo - Only for admins"""
    # Check if user is admin
    if message.from_user.id not in ADMINS:
        return await message.reply("<b>🚫 Access Denied. This command is for admins only.</b>")
    
    status_msg = await message.reply("⏳")
    try:
        channels = await get_channels()
        if not channels:
            await status_msg.delete()
            return await message.reply(
                "<b><blockquote expandable>No channels available. Please use /addch to add a channel.</b>"
            )
        await send_links_page(client, message, channels, 0, status_msg)
    except Exception as e:
        await status_msg.delete()
        await message.reply(f"<b>Error:</b> <code>{str(e)}</code>")

async def send_links_page(client, message, channels, page, status_msg=None, edit=False):
    """Send links page with pagination and photo"""
    if status_msg:
        await status_msg.delete()
        
    total_pages = (len(channels) + PAGE_SIZE - 1) // PAGE_SIZE
    start_idx = page * PAGE_SIZE
    end_idx = start_idx + PAGE_SIZE
    
    # Create caption text
    caption = "<b>📊 All Channel Links</b>\n\n"
    
    # Process channels concurrently
    tasks = []
    for channel_id in channels[start_idx:end_idx]:
        tasks.append(asyncio.gather(
            get_chat_info(client, channel_id),
            save_encoded_link(channel_id),
            encode(str(channel_id)),
            return_exceptions=True
        ))
    
    try:
        results = await asyncio.gather(*tasks, return_exceptions=True)
    except Exception as e:
        print(f"Error gathering link info: {e}")
        results = [None] * len(channels[start_idx:end_idx])
    
    for i, result in enumerate(results):
        idx = start_idx + i + 1
        channel_id = channels[start_idx + i]
        
        if isinstance(result, Exception) or result is None:
            print(f"Error getting info for channel {channel_id}: {result}")
            caption += f"<b>{idx}. Channel {channel_id}</b> (Error)\n\n"
            continue
            
        try:
            chat_info, base64_invite, base64_request = result
            if isinstance(chat_info, Exception):
                caption += f"<b>{idx}. Channel {channel_id}</b> (Error)\n\n"
                continue
                
            await save_encoded_link2(channel_id, base64_request)
            normal_link = f"https://t.me/{client.username}?start={base64_invite}"
            request_link = f"https://t.me/{client.username}?start=req_{base64_request}"
            
            caption += f"<b>{idx}. {chat_info.title}</b>\n"
            caption += f"<b>   🔗 Normal:</b> <code>{normal_link}</code>\n"
            caption += f"<b>   🔗 Request:</b> <code>{request_link}</code>\n\n"
            
        except Exception as e:
            print(f"Error for channel {channel_id}: {e}")
            caption += f"<b>{idx}. Channel {channel_id}</b> (Error)\n\n"
    
    caption += f"<b>📄 Page {page + 1} of {total_pages}</b>"
    
    # Navigation buttons
    buttons = []
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("◀️ Previous", callback_data=f"linkspage_{page-1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("Next ▶️", callback_data=f"linkspage_{page+1}"))
    
    if nav_buttons:
        buttons.append(nav_buttons)
    
    reply_markup = InlineKeyboardMarkup(buttons) if buttons else None
    
    try:
        if edit:
            # For callback queries, we can only edit text messages, so check if we can edit with photo
            try:
                await message.edit_media(
                    media=InputMediaPhoto(
                        DEFAULT_LINKS_PHOTO,
                        caption=caption
                    ),
                    reply_markup=reply_markup
                )
            except:
                # Fallback to text editing if photo editing fails
                await message.edit_text(caption, reply_markup=reply_markup)
        else:
            # For new messages, send with photo
            await message.reply_photo(
                photo=DEFAULT_LINKS_PHOTO,
                caption=caption,
                reply_markup=reply_markup
            )
    except Exception as e:
        print(f"Error sending photo message: {e}")
        # Fallback to text message
        if edit:
            await message.edit_text(caption, reply_markup=reply_markup)
        else:
            await message.reply(caption, reply_markup=reply_markup)

@Client.on_callback_query(filters.regex(r"linkspage_(\d+)"))
async def paginate_links(client: Client, callback_query):
    """Handle pagination for links pages"""
    # Check if user is admin
    if callback_query.from_user.id not in ADMINS:
        await callback_query.answer("🚫 Access Denied. Admins only.", show_alert=True)
        return
    
    page = int(callback_query.data.split("_")[1])
    status_msg = await callback_query.message.edit_text("⏳")
    channels = await get_channels()
    await send_links_page(client, callback_query.message, channels, page, status_msg, edit=True)

@Client.on_message(filters.command('bulklink') & filters.private)
async def bulk_link(client: Client, message: Message):
    """Generate links for multiple channels at once - Only for admins"""
    # Check if user is admin
    if message.from_user.id not in ADMINS:
        return await message.reply("<b>🚫 Access Denied. This command is for admins only.</b>")
    
    if len(message.command) < 2:
        return await message.reply(
            "<b><blockquote expandable>Usage: <code>/bulklink &lt;id1&gt; &lt;id2&gt; ...</code></b>"
        )

    ids = message.command[1:]
    caption = "<b>📦 Bulk Link Generation</b>\n\n"
    
    for idx, id_str in enumerate(ids, start=1):
        try:
            channel_id = int(id_str)
            chat = await client.get_chat(channel_id)
            normal_link, request_link = await generate_channel_links(client, channel_id)
            
            caption += f"<b>{idx}. {chat.title} ({channel_id})</b>\n"
            caption += f"<b>   🔗 Normal:</b> <code>{normal_link}</code>\n"
            caption += f"<b>   🔗 Request:</b> <code>{request_link}</code>\n\n"
            
        except Exception as e:
            caption += f"<b>{idx}. Channel {id_str}</b> (Error: {e})\n\n"
    
    try:
        await message.reply_photo(
            photo=DEFAULT_LINKS_PHOTO,
            caption=caption
        )
    except Exception:
        await message.reply(caption)

@Client.on_message(filters.command('genlink') & filters.private)
async def generate_link_command(client: Client, message: Message):
    """Generate links for external URLs - Only for admins"""
    # Check if user is admin
    if message.from_user.id not in ADMINS:
        return await message.reply("<b>🚫 Access Denied. This command is for admins only.</b>")
    
    if len(message.command) < 2:
        return await message.reply("<b>Usage:</b> <code>/genlink &lt;link&gt;</code>")

    link = message.command[1]
    try:
        sent_msg = await client.send_message(DATABASE_CHANNEL, f"#LINK\n{link}")
        channel_id = sent_msg.id
        
        # Save encoded links
        base64_invite = await save_encoded_link(channel_id)
        base64_request = await encode(str(channel_id))
        await save_encoded_link2(channel_id, base64_request)
        
        # Store the original link in the database
        from database.database import channels_collection
        await channels_collection.update_one(
            {"channel_id": channel_id},
            {"$set": {"original_link": link}},
            upsert=True
        )
        
        normal_link = f"https://t.me/{client.username}?start={base64_invite}"
        request_link = f"https://t.me/{client.username}?start=req_{base64_request}"
        
        reply_text = (
            f"<b>✅ Link stored and encoded successfully.</b>\n\n"
            f"<b>🔗 Normal Link:</b> <code>{normal_link}</code>\n"
            f"<b>🔗 Request Link:</b> <code>{request_link}</code>"
        )
        await message.reply(reply_text)
    except Exception as e:
        await message.reply(f"<b>Error storing link:</b> <code>{e}</code>")

@Client.on_message(filters.command('channels') & filters.private)
async def show_channel_ids(client: Client, message: Message):
    """Show all channel IDs and names - Only for admins"""
    # Check if user is admin
    if message.from_user.id not in ADMINS:
        return await message.reply("<b>🚫 Access Denied. This command is for admins only.</b>")
    
    status_msg = await message.reply("⏳")
    try:
        channels = await get_channels()
        if not channels:
            await status_msg.delete()
            return await message.reply(
                "<b><blockquote expandable>No channels available. Please use /addch to add a channel.</b>"
            )
            
        await send_channel_ids_page(client, message, channels, 0, status_msg)
    except Exception as e:
        await status_msg.delete()
        await message.reply(f"<b>Error:</b> <code>{str(e)}</code>")

async def send_channel_ids_page(client, message, channels, page, status_msg=None, edit=False):
    """Send channel IDs page with photo"""
    if status_msg:
        await status_msg.delete()
        
    PAGE_SIZE = 10
    total_pages = (len(channels) + PAGE_SIZE - 1) // PAGE_SIZE
    start_idx = page * PAGE_SIZE
    end_idx = start_idx + PAGE_SIZE
    
    # Get all chat info concurrently
    chat_tasks = [get_chat_info(client, channel_id) for channel_id in channels[start_idx:end_idx]]
    
    try:
        chat_infos = await asyncio.gather(*chat_tasks, return_exceptions=True)
    except Exception as e:
        print(f"Error gathering chat info: {e}")
        chat_infos = [None] * len(channels[start_idx:end_idx])
    
    caption = "<b>📋 Connected Channels (ID & Name)</b>\n\n"
    
    for i, chat_info in enumerate(chat_infos):
        idx = start_idx + i + 1
        channel_id = channels[start_idx + i]
        
        if isinstance(chat_info, Exception) or chat_info is None:
            caption += f"<b>{idx}. Channel {channel_id}</b> (Error)\n"
            continue
            
        caption += f"<b>{idx}. {chat_info.title}</b> <code>({channel_id})</code>\n"
        
    caption += f"\n<b>📄 Page {page + 1} of {total_pages}</b>"
    
    # Navigation buttons
    buttons = []
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("◀️ Previous", callback_data=f"channelids_{page-1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("Next ▶️", callback_data=f"channelids_{page+1}"))
    
    if nav_buttons:
        buttons.append(nav_buttons)
        
    reply_markup = InlineKeyboardMarkup(buttons) if buttons else None
    
    try:
        if edit:
            try:
                await message.edit_media(
                    media=InputMediaPhoto(
                        DEFAULT_LINKS_PHOTO,
                        caption=caption
                    ),
                    reply_markup=reply_markup
                )
            except:
                await message.edit_text(caption, reply_markup=reply_markup)
        else:
            await message.reply_photo(
                photo=DEFAULT_LINKS_PHOTO,
                caption=caption,
                reply_markup=reply_markup
            )
    except Exception as e:
        print(f"Error sending photo message: {e}")
        if edit:
            await message.edit_text(caption, reply_markup=reply_markup)
        else:
            await message.reply(caption, reply_markup=reply_markup)

@Client.on_callback_query(filters.regex(r"channelids_(\d+)"))
async def paginate_channel_ids(client: Client, callback_query):
    """Handle pagination for channel IDs pages"""
    # Check if user is admin
    if callback_query.from_user.id not in ADMINS:
        await callback_query.answer("🚫 Access Denied. Admins only.", show_alert=True)
        return
    
    page = int(callback_query.data.split("_")[1])
    status_msg = await callback_query.message.edit_text("⏳")
    channels = await get_channels()
    await send_channel_ids_page(client, callback_query.message, channels, page, status_msg, edit=True)
