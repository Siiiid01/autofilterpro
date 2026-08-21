import asyncio
import logging
import random

from info import APPROVED, AUTO_APPROVE_CHAT_IDS, PICS, SUPPORT_CHAT, TEXT, ADMINS
from pyrogram import Client, filters
from pyrogram.types import ChatJoinRequest, InlineKeyboardButton, InlineKeyboardMarkup, Message


APPROVAL_WAIT_TIME = 10
logger = logging.getLogger(__name__)

join_request_filter = filters.group | filters.channel
if AUTO_APPROVE_CHAT_IDS:
    join_request_filter &= filters.chat(AUTO_APPROVE_CHAT_IDS)


@Client.on_chat_join_request(join_request_filter)
async def autoapprove(client, message: ChatJoinRequest):
    """Approve requests after the configured delay and optionally welcome the user."""
    chat = message.chat
    user = message.from_user
    logger.info("%s requested to join %s", user.first_name, chat.title)

    await asyncio.sleep(APPROVAL_WAIT_TIME)

    try:
        await client.approve_chat_join_request(chat_id=chat.id, user_id=user.id)
    except Exception:
        logger.exception(
            "Could not approve join request for user %s in chat %s", user.id, chat.id
        )
        return

    if APPROVED != "on":
        return

    try:
        invite_link = await client.export_chat_invite_link(chat.id)
        buttons = [
            [InlineKeyboardButton("Join support", url=SUPPORT_CHAT)],
            [InlineKeyboardButton(f"Join {chat.title}", url=invite_link)],
        ]
        caption = TEXT.format(
            mention=user.mention,
            title=chat.title or "this chat",
        )
        await client.send_photo(
            chat_id=user.id,
            photo=random.choice(PICS),
            caption=caption,
            reply_markup=InlineKeyboardMarkup(buttons),
        )
    except Exception:
        # The request is already approved. Missing private-chat access or invite
        # permissions must not turn a completed request into a handler failure.
        logger.exception("Could not send join-request welcome to user %s", user.id)


@Client.on_message(filters.command("reqtime") & filters.user(ADMINS))
async def set_reqtime(client, message: Message):
    global APPROVAL_WAIT_TIME

    if len(message.command) != 2 or not message.command[1].isdigit():
        await message.reply_text("Usage: /reqtime <seconds>")
        return

    APPROVAL_WAIT_TIME = int(message.command[1])
    await message.reply_text(
        f"Request approval time has been set to {APPROVAL_WAIT_TIME} seconds."
    )
