# @NaapaExtra

import base64
import re
import asyncio
import humanize
from pyrogram import filters, Client
from pyrogram.enums import ChatMemberStatus, ParseMode
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import UserNotParticipant, Forbidden, PeerIdInvalid, ChatAdminRequired, FloodWait
from datetime import datetime, timedelta

async def encode(string):
    string_bytes = string.encode("ascii")
    base64_bytes = base64.urlsafe_b64encode(string_bytes)
    base64_string = (base64_bytes.decode("ascii")).strip("=")
    return base64_string

async def decode(base64_string):
    base64_string = base64_string.strip("=")
    base64_bytes = (base64_string + "=" * (-len(base64_string) % 4)).encode("ascii")
    string_bytes = base64.urlsafe_b64decode(base64_bytes) 
    string = string_bytes.decode("ascii")
    return string

async def get_messages(client, message_ids):
    messages = []
    total_messages = 0
    while total_messages != len(message_ids):
        temb_ids = message_ids[total_messages:total_messages+200]
        try:
            msgs = await client.get_messages(
                chat_id=client.db_channel.id,
                message_ids=temb_ids
            )
        except FloodWait as e:
            await asyncio.sleep(e.x)
            msgs = await client.get_messages(
                chat_id=client.db_channel.id,
                message_ids=temb_ids
            )
        except:
            pass
        total_messages += len(temb_ids)
        messages.extend(msgs)
    return messages

async def get_message_id(client, message):
    if message.forward_from_chat:
        if message.forward_from_chat.id == client.db_channel.id:
            return message.forward_from_message_id
        else:
            return 0
    elif message.forward_sender_name:
        return 0
    elif message.text:
        pattern = r"https://t.me/(?:c/)?(.*)/(\d+)"
        matches = re.match(pattern,message.text)
        if not matches:
            return 0
        channel_id = matches.group(1)
        msg_id = int(matches.group(2))
        if channel_id.isdigit():
            if f"-100{channel_id}" == str(client.db_channel.id):
                return msg_id
        else:
            if channel_id == client.db_channel.username:
                return msg_id
    else:
        return 0

def get_readable_time(seconds: int) -> str:
    count = 0
    up_time = ""
    time_list = []
    time_suffix_list = ["s", "m", "h", "days"]
    while count < 4:
        count += 1
        remainder, result = divmod(seconds, 60) if count < 3 else divmod(seconds, 24)
        if seconds == 0 and remainder == 0:
            break
        time_list.append(int(result))
        seconds = int(remainder)
    hmm = len(time_list)
    for x in range(hmm):
        time_list[x] = str(time_list[x]) + time_suffix_list[x]
    if len(time_list) == 4:
        up_time += f"{time_list.pop()}, "
    time_list.reverse()
    up_time += ":".join(time_list)
    return up_time

async def is_bot_admin(client, channel_id):
    try:
        bot = await client.get_chat_member(channel_id, "me")
        if bot.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
            if bot.privileges:
                required_rights = ["can_invite_users", "can_delete_messages"]
                missing_rights = [right for right in required_rights if not getattr(bot.privileges, right, False)]
                if missing_rights:
                    return False, f"Bot is missing the following rights: {', '.join(missing_rights)}"
            return True, None
        return False, "Bot is not an admin in the channel."
    except ChatAdminRequired:
        return False, "Bot lacks permission to access admin information in this channel."
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"

async def check_subscription(client, user_id):
    statuses = {}
    for channel_id, (channel_name, channel_link, request, timer) in client.fsub_dict.items():
        if request:
            send_req = await client.mongodb.is_user_in_channel(channel_id, user_id)
            if send_req:
                statuses[channel_id] = ChatMemberStatus.MEMBER
                continue
        try:
            user = await client.get_chat_member(channel_id, user_id)
            statuses[channel_id] = user.status
        except UserNotParticipant:
            statuses[channel_id] = ChatMemberStatus.BANNED
        except Forbidden:
            statuses[channel_id] = None
        except Exception:
            statuses[channel_id] = None
    return statuses

def is_user_subscribed(statuses):
    return all(
        status in {ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER}
        for status in statuses.values() if status is not None
    ) and bool(statuses)

def force_sub(func):
    async def wrapper(client: Client, message: Message):
        if not client.fsub_dict:
            return await func(client, message)
        
        photo = client.messages.get('FSUB_PHOTO', '')
        if photo:
            msg = await message.reply_photo(caption="<code>Checking subscription...</code>", photo=photo)
        else:
            msg = await message.reply("<code>Checking subscription...</code>")
            
        user_id = message.from_user.id
        statuses = await check_subscription(client, user_id)

        if is_user_subscribed(statuses):
            await msg.delete()
            return await func(client, message)

        buttons = []
        channels_message = f"{client.messages.get('FSUB', '')}\n\n<b>Please join the following channel(s):</b>"

        for channel_id, (channel_name, channel_link, request, timer) in client.fsub_dict.items():
            status = statuses.get(channel_id, None)
            if status not in {ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER}:
                if timer > 0:
                    expire_time = datetime.now() + timedelta(minutes=timer)
                    invite = await client.create_chat_invite_link(
                        chat_id=channel_id,
                        expire_date=expire_time,
                        creates_join_request=request
                    )
                    channel_link = invite.invite_link
                buttons.append(InlineKeyboardButton(channel_name, url=channel_link))

        from_link = message.text.split(" ")
        if len(from_link) > 1:
            try:
                base64.urlsafe_b64decode(from_link[1] + '==')
                try_again_link = f"https://t.me/{client.username}?start={from_link[1]}"
                buttons.append(InlineKeyboardButton("Try Again", url=try_again_link))
            except (base64.binascii.Error, Exception):
                pass

        buttons_markup = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]
        
        if len(from_link) > 1 and buttons and "Try Again" in buttons[-1].text:
             buttons_markup.append([buttons.pop()])
             
        final_markup = InlineKeyboardMarkup(buttons_markup) if buttons_markup else None

        try:
            await msg.edit_text(
                text=channels_message,
                reply_markup=final_markup,
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            client.LOGGER(__name__, client.name).warning(f"Error updating FSUB message: {e}")

    return wrapper

async def send_files(client: Client, chat_id: int, base64_string: str):
    try:
        string = await decode(base64_string)
        parts = string.split("-")
        
        if parts[0] != "get" or len(parts) not in [2, 3]:
            return await client.send_message(chat_id, "⚠️ **Invalid or corrupted file link.**")

        msg_id = int(int(parts[1]) / abs(client.db_channel.id))
        end_msg_id = msg_id
        if len(parts) == 3: end_msg_id = int(int(parts[2]) / abs(client.db_channel.id))
        
        message_ids = list(range(msg_id, end_msg_id + 1))
        progress_msg = await client.send_message(chat_id, "⏳ Please wait, fetching your file(s)...")
        
        file_messages = await get_messages(client, message_ids)
        await progress_msg.delete()

        if not file_messages: 
            return await client.send_message(chat_id, "❌ **Files not found.**")
        
        sent_messages = []
        for msg in file_messages:
            try:
                sent = await msg.copy(chat_id=chat_id, protect_content=client.protect)
                sent_messages.append(sent)
                await asyncio.sleep(0.5)
            except Exception as e: 
                client.LOGGER(__name__, "SEND").warning(f"Failed to send {getattr(msg, 'id', 'N/A')} to {chat_id}: {e}")
        
        if sent_messages and client.auto_del > 0:
            del_msg = await client.send_message(chat_id=chat_id, text=f'<blockquote><i><b>These files will be deleted in {humanize.naturaldelta(client.auto_del)}.</b></i></blockquote>')
            
            async def _delete_task():
                await asyncio.sleep(client.auto_del)
                try:
                    ids_to_del = [m.id for m in sent_messages if m]
                    if ids_to_del:
                        await client.delete_messages(chat_id, ids_to_del)
                    if del_msg:
                        await del_msg.delete()
                except Exception as e:
                    client.LOGGER(__name__, "AUTO_DELETE").error(f"Error during auto-deletion: {e}")
            
            asyncio.create_task(_delete_task())

        # --- THIS IS THE CRITICAL ADDITION ---
        # After successfully sending all files, set the bypass timer for the user.
        try:
            await client.mongodb.set_bypass_timer(chat_id)
            client.LOGGER(__name__, "BYPASS").debug(f"Bypass timer set for user {chat_id}.")
        except Exception as e:
            client.LOGGER(__name__, "BYPASS_ERROR").error(f"Failed to set bypass timer for {chat_id}: {e}")
        # ------------------------------------

    except Exception as e:
        client.LOGGER(__name__, "SEND_FILES").error(f"Error in send_files for chat {chat_id}: {e}", exc_info=True)
        try:
            await client.send_message(chat_id, "An unexpected error occurred while processing your request.")
        except Exception:
            pass
