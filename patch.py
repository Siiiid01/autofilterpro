import asyncio
import logging
from pyrogram.types import Message
from info import DELETE_TIME

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# WHITELIST — messages that must NEVER be auto-deleted by this patch.
# ─────────────────────────────────────────────────────────────────────────────
_WHITELIST_TEXT = [
    # indexing
    "index", "messages fetched", "starting indexing", "successfully saved",
    "successfully cancelled",
    # search results / file listing
    "searching", "files found", "sᴇᴀʀᴄʜ", "select option", "send all",
    # batch/link delivery
    "please wait", "generating link", "here is your link", "contains",
    "batch", "dstore",
    # file delivery warning (commands.py manages its own deletion via _delete_after)
    "important", "will be deleted", "forward this file",
    # verification prompt shown to user
    "not verified", "verify", "verification",
    # admin messages
    "do you want to index",
]

_WHITELIST_CALLBACKS = [
    "index", "index_cancel", "file#", "filep#", "next_", "prev_",
    "sendfiles", "qualities", "languages", "seasons", "checksub",
    "generate_stream_link", "pages", "reqinfo", "delfile",
]


def _should_skip(bot_msg) -> bool:
    """Return True if this message should NOT be auto-deleted by the patch."""
    if bot_msg is None:
        return True

    text = (getattr(bot_msg, 'text', '') or
            getattr(bot_msg, 'caption', '') or '').lower()

    for keyword in _WHITELIST_TEXT:
        if keyword in text:
            return True

    markup = getattr(bot_msg, 'reply_markup', None)
    if markup and hasattr(markup, 'inline_keyboard'):
        for row in markup.inline_keyboard:
            for btn in row:
                cb = getattr(btn, 'callback_data', '') or ''
                for kw in _WHITELIST_CALLBACKS:
                    if kw in cb:
                        return True
                btn_text = (getattr(btn, 'text', '') or '').lower()
                for keyword in _WHITELIST_TEXT:
                    if keyword in btn_text:
                        return True

    return False


# Keep original methods
_orig_reply_text = Message.reply_text
_orig_reply_photo = Message.reply_photo
_orig_reply_document = Message.reply_document
_orig_reply_video = Message.reply_video
_orig_reply_audio = Message.reply_audio
_orig_reply_animation = Message.reply_animation
_orig_reply_sticker = Message.reply_sticker

async def _auto_delete_task(bot_msg, delay):
    """Wait for the delay and then delete the bot's reply."""
    await asyncio.sleep(delay)
    try:
        await bot_msg.delete()
    except Exception:
        pass

from pyrogram.enums import ChatType
from pyrogram import Client

def _wrap_reply(original_func):
    async def wrapped_reply(self, *args, **kwargs):
        # 1. Call the original reply method
        bot_msg = await original_func(self, *args, **kwargs)

        # 2. Delete the user's command/message only in PM
        try:
            if hasattr(self, "chat") and self.chat and getattr(self.chat, "type", None) == ChatType.PRIVATE:
                await self.delete()
        except Exception:
            pass

        # 3. Skip auto-delete for whitelisted messages
        if _should_skip(bot_msg):
            return bot_msg

        # 4. Verification messages get a longer window (5 min)
        is_verify = False
        markup = getattr(bot_msg, 'reply_markup', None)
        if markup and hasattr(markup, 'inline_keyboard'):
            for row in markup.inline_keyboard:
                for btn in row:
                    btn_text = (getattr(btn, 'text', '') or '').lower()
                    if 'ᴠᴇʀɪғʏ' in btn_text or 'verify' in btn_text:
                        is_verify = True

        delay = 300 if is_verify else DELETE_TIME
        asyncio.create_task(_auto_delete_task(bot_msg, delay))
        return bot_msg

    return wrapped_reply

def _wrap_client_send(original_func):
    async def wrapped_send(self, *args, **kwargs):
        bot_msg = await original_func(self, *args, **kwargs)

        # Skip auto-delete for whitelisted messages
        if _should_skip(bot_msg):
            return bot_msg

        # Verification messages get a longer window
        is_verify = False
        markup = getattr(bot_msg, 'reply_markup', None)
        if markup and hasattr(markup, 'inline_keyboard'):
            for row in markup.inline_keyboard:
                for btn in row:
                    btn_text = (getattr(btn, 'text', '') or '').lower()
                    if 'ᴠᴇʀɪғʏ' in btn_text or 'verify' in btn_text:
                        is_verify = True

        delay = 300 if is_verify else DELETE_TIME
        asyncio.create_task(_auto_delete_task(bot_msg, delay))
        return bot_msg

    return wrapped_send

# Apply patches
Message.reply_text = _wrap_reply(_orig_reply_text)
Message.reply_photo = _wrap_reply(_orig_reply_photo)
Message.reply_document = _wrap_reply(_orig_reply_document)
Message.reply_video = _wrap_reply(_orig_reply_video)
Message.reply_audio = _wrap_reply(_orig_reply_audio)
Message.reply_animation = _wrap_reply(_orig_reply_animation)
Message.reply_sticker = _wrap_reply(_orig_reply_sticker)

_orig_send_message = Client.send_message
_orig_send_cached_media = Client.send_cached_media

Client.send_message = _wrap_client_send(_orig_send_message)
Client.send_cached_media = _wrap_client_send(_orig_send_cached_media)

_orig_delete = Message.delete

async def safe_delete(self, *args, **kwargs):
    try:
        return await _orig_delete(self, *args, **kwargs)
    except Exception:
        return False

Message.delete = safe_delete

logger.info("Auto-delete global patch applied successfully.")
