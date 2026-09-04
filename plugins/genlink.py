import base64
import logging
import re

from pyrogram import Client, enums, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.errors.exceptions.bad_request_400 import (
    ChannelInvalid,
    UsernameInvalid,
    UsernameNotModified,
)

from info import CHANNELS, OWNERID
from utils import temp


logger = logging.getLogger(__name__)


async def owner_only(_, __, message):
    allowed = bool(message.from_user and message.from_user.id == OWNERID)
    if not allowed:
        logger.warning(
            "GENLINK_UNAUTHORIZED command=%s user_id=%s",
            getattr(message, "command", ["unknown"])[0],
            getattr(getattr(message, "from_user", None), "id", None),
        )
    return allowed


def encode_payload(payload):
    return base64.urlsafe_b64encode(payload.encode("ascii")).decode().rstrip("=")


def source_message(message):
    """Return the original channel and message IDs from a forwarded post."""
    forwarded_chat = getattr(message, "forward_from_chat", None)
    forwarded_id = getattr(message, "forward_from_message_id", None)
    if forwarded_chat and forwarded_id:
        return forwarded_chat.id, forwarded_id

    forward_origin = getattr(message, "forward_origin", None)
    origin_chat = getattr(forward_origin, "chat", None)
    origin_id = getattr(forward_origin, "message_id", None)
    if origin_chat and origin_id:
        return origin_chat.id, origin_id
    return None, None


def is_database_channel(chat_id):
    return any(str(channel_id) == str(chat_id) for channel_id in CHANNELS)


@Client.on_message(filters.command(["link"]) & filters.create(owner_only))
async def gen_link(bot, message):
    replied = message.reply_to_message
    if not replied:
        prompt = await message.reply(
            "<blockquote>ꜰᴏʀᴡᴀʀᴅ ᴍᴇssᴀɢᴇ ꜰʀᴏᴍ ᴛʜᴇ ᴅʙ ᴄʜᴀɴɴᴇʟ (ᴡɪᴛʜ ǫᴜᴏᴛᴇs)..</blockquote>"
        )
        try:
            replied = await bot.listen(
                chat_id=message.chat.id,
                filters=filters.forwarded,
                timeout=60,
            )
        except Exception:
            logger.exception("GENLINK_LISTEN_FAILED owner_id=%s", message.from_user.id)
            return await prompt.edit("Timed out. Please run /link and forward the channel post again.")

    chat_id, message_id = source_message(replied)
    if not chat_id or not message_id or not is_database_channel(chat_id):
        logger.warning(
            "GENLINK_INVALID_SOURCE owner_id=%s chat_id=%s message_id=%s configured_channels=%s",
            getattr(message.from_user, "id", None), chat_id, message_id, CHANNELS,
        )
        return await message.reply(
            "This message is not from a configured database channel. Forward the original channel post and try again."
        )

    payload = encode_payload(f"CF-{chat_id}-{message_id}")
    logger.info(
        "GENLINK_CREATED owner_id=%s source_chat_id=%s source_message_id=%s",
        message.from_user.id, chat_id, message_id,
    )
    link = f"https://t.me/{temp.U_NAME}?start={payload}"
    return await message.reply(
        f"<blockquote>✓ ʜᴇʀᴇ ɪs ʏᴏᴜʀ ʟɪɴᴋ</blockquote>\n\n<code>{link}</code>",
        parse_mode=enums.ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔁 sʜᴀʀᴇ ᴜʀʟ", url=f"https://telegram.me/share/url?url={link}")]
        ]),
    )


@Client.on_message(filters.command(["batch"]) & filters.create(owner_only))
async def gen_link_batch(bot, message):
    parts = message.text.strip().split()
    if len(parts) != 3:
        return await message.reply(
            "Use:\n<code>/batch https://t.me/c/CHANNEL_ID/FIRST https://t.me/c/CHANNEL_ID/LAST</code>"
        )

    _, first, last = parts
    link_pattern = re.compile(
        r"^(?:https://)?(?:t\.me|telegram\.me|telegram\.dog)/(?:c/)?(-?\d+|[A-Za-z0-9_]+)/([0-9]+)$"
    )
    first_match = link_pattern.match(first)
    last_match = link_pattern.match(last)
    if not first_match or not last_match:
        return await message.reply("Invalid Telegram message link.")

    first_chat, first_id = first_match.group(1), int(first_match.group(2))
    last_chat, last_id = last_match.group(1), int(last_match.group(2))
    if first_chat != last_chat:
        return await message.reply("Both links must belong to the same database channel.")

    chat_id = int(f"-100{first_chat}") if first_chat.isdigit() else first_chat
    try:
        resolved_chat = (await bot.get_chat(chat_id)).id
    except ChannelInvalid:
        logger.exception("GENBATCH_CHANNEL_INVALID chat_id=%s", chat_id)
        return await message.reply("I cannot access that channel. Make sure I am an administrator there.")
    except (UsernameInvalid, UsernameNotModified):
        logger.exception("GENBATCH_CHANNEL_INVALID_NAME chat_id=%s", chat_id)
        return await message.reply("Invalid database channel link.")
    except Exception:
        logger.exception("GENBATCH_GET_CHAT_FAILED chat_id=%s", chat_id)
        return await message.reply("I could not access that channel right now.")

    if not is_database_channel(resolved_chat):
        logger.warning(
            "GENBATCH_SOURCE_NOT_CONFIGURED source_chat_id=%s configured_channels=%s",
            resolved_chat, CHANNELS,
        )
        return await message.reply("That channel is not configured as a database channel.")

    start_id, end_id = sorted((first_id, last_id))
    payload = encode_payload(f"CB-{resolved_chat}-{start_id}-{end_id}")
    logger.info(
        "GENBATCH_CREATED owner_id=%s source_chat_id=%s first_id=%s last_id=%s",
        message.from_user.id, resolved_chat, start_id, end_id,
    )
    link = f"https://t.me/{temp.U_NAME}?start={payload}"
    return await message.reply(
        f"<blockquote>✓ ʜᴇʀᴇ ɪs ʏᴏᴜʀ ʙᴀᴛᴄʜ ʟɪɴᴋ</blockquote>\n\n"
        f"<b>ᴍᴇssᴀɢᴇs:</b> <code>{start_id} - {end_id}</code>\n\n<code>{link}</code>",
        parse_mode=enums.ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔁 sʜᴀʀᴇ ᴜʀʟ", url=f"https://telegram.me/share/url?url={link}")]
        ]),
    )
