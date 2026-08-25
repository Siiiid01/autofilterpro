import asyncio
import logging
from pyrogram.types import Message
from info import DELETE_TIME

logger = logging.getLogger(__name__)

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
    except Exception as e:
        pass

def _wrap_reply(original_func):
    async def wrapped_reply(self, *args, **kwargs):
        # 1. Call the original reply method
        bot_msg = await original_func(self, *args, **kwargs)
        
        # 2. Delete the user's command/message immediately
        try:
            await self.delete()
        except Exception:
            pass

        # 3. Determine the auto-delete delay
        # If it's a verification message (checking text or reply_markup)
        is_verify = False
        
        # Check text
        text = getattr(bot_msg, 'text', '') or getattr(bot_msg, 'caption', '') or ''
        if text and ('verify' in text.lower() or 'verification' in text.lower()):
            is_verify = True
            
        # Check buttons
        markup = getattr(bot_msg, 'reply_markup', None)
        if markup and hasattr(markup, 'inline_keyboard'):
            for row in markup.inline_keyboard:
                for btn in row:
                    if btn.text and ('verify' in btn.text.lower() or 'verification' in btn.text.lower() or 'ᴠᴇʀɪғʏ' in btn.text):
                        is_verify = True

        # Use 300 seconds (5 min) for verify prompts, else default DELETE_TIME
        delay = 300 if is_verify else DELETE_TIME
        
        # 4. Spawn background task to delete bot's reply
        if bot_msg:
            asyncio.create_task(_auto_delete_task(bot_msg, delay))
            
        return bot_msg
        
    return wrapped_reply

# Apply patches
Message.reply_text = _wrap_reply(_orig_reply_text)
Message.reply_photo = _wrap_reply(_orig_reply_photo)
Message.reply_document = _wrap_reply(_orig_reply_document)
Message.reply_video = _wrap_reply(_orig_reply_video)
Message.reply_audio = _wrap_reply(_orig_reply_audio)
Message.reply_animation = _wrap_reply(_orig_reply_animation)
Message.reply_sticker = _wrap_reply(_orig_reply_sticker)

_orig_delete = Message.delete

async def safe_delete(self, *args, **kwargs):
    try:
        return await _orig_delete(self, *args, **kwargs)
    except Exception:
        return False

Message.delete = safe_delete

logger.info("Auto-delete global patch applied successfully.")
