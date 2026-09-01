"""
errors.py — Centralised error handling for AutoFilterPro.

Usage in any module:
    from errors import log_exception, handle_flood_wait, safe_send_log, BotError

Every key except-block should call log_exception() so errors surface in Koyeb logs.
"""

import logging
import traceback
import asyncio
import functools

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Custom Exception Hierarchy
# ─────────────────────────────────────────────

class BotError(Exception):
    """Base exception for bot-level errors with structured context."""
    def __init__(self, message: str, user_id=None, chat_id=None, handler=None):
        super().__init__(message)
        self.user_id = user_id
        self.chat_id = chat_id
        self.handler = handler

    def __str__(self):
        base = super().__str__()
        ctx = []
        if self.handler:
            ctx.append(f"handler={self.handler}")
        if self.user_id:
            ctx.append(f"user_id={self.user_id}")
        if self.chat_id:
            ctx.append(f"chat_id={self.chat_id}")
        return f"{base} [{', '.join(ctx)}]" if ctx else base


class DatabaseError(BotError):
    """Raised on MongoDB / database failures."""
    pass


class VerificationError(BotError):
    """Raised during verification flow failures."""
    pass


class StreamError(BotError):
    """Raised during file streaming failures."""
    pass


# ─────────────────────────────────────────────
# Core Logging Utility
# ─────────────────────────────────────────────

def log_exception(log: logging.Logger, exc: Exception, **ctx):
    """
    Log an exception with full traceback and context to both the Python logger
    (which Koyeb captures) and stderr. Always call this instead of bare `pass`
    or `print(e)` in except blocks.

    Example:
        except Exception as e:
            log_exception(logger, e, user_id=user_id, handler="start")
    """
    ctx_str = " | ".join(f"{k}={v}" for k, v in ctx.items()) if ctx else "no context"
    tb = traceback.format_exc()
    log.error(
        f"[ERROR] {type(exc).__name__}: {exc}\n"
        f"Context: {ctx_str}\n"
        f"Traceback:\n{tb}"
    )


# ─────────────────────────────────────────────
# FloodWait Helper (Pyrofork-compatible)
# ─────────────────────────────────────────────

async def handle_flood_wait(exc, log: logging.Logger = None):
    """
    Sleep for the required FloodWait duration.
    Uses `.value` (Pyrofork) with fallback to `.x` (older Pyrogram).

    Example:
        except FloodWait as e:
            await handle_flood_wait(e, logger)
    """
    wait = getattr(exc, 'value', None) or getattr(exc, 'x', None) or 5
    if log:
        log.warning(f"FloodWait: sleeping {wait}s")
    await asyncio.sleep(wait)


# ─────────────────────────────────────────────
# Safe Log-Channel Sender
# ─────────────────────────────────────────────

async def safe_send_log(client, channel_id: int, text: str):
    """
    Send a message to the log channel without raising.
    Falls back to logger.error if the send fails.

    Example:
        await safe_send_log(client, LOG_CHANNEL, f"Error: {e}")
    """
    try:
        await client.send_message(chat_id=channel_id, text=text)
    except Exception as e:
        logger.error(f"safe_send_log failed (channel={channel_id}): {e}")


# ─────────────────────────────────────────────
# Retry Decorator
# ─────────────────────────────────────────────

def async_retry(max_retries: int = 3, backoff: float = 1.0, exceptions=(Exception,)):
    """
    Decorator: retries an async function up to max_retries times on given exceptions,
    with exponential backoff. Logs each retry attempt.

    Example:
        @async_retry(max_retries=3, backoff=2.0)
        async def risky_api_call():
            ...
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            attempt = 0
            delay = backoff
            while attempt < max_retries:
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    attempt += 1
                    if attempt >= max_retries:
                        logger.error(
                            f"[async_retry] {func.__name__} failed after {max_retries} attempts: {e}"
                        )
                        raise
                    logger.warning(
                        f"[async_retry] {func.__name__} attempt {attempt}/{max_retries} failed: {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    await asyncio.sleep(delay)
                    delay *= 2  # exponential backoff
        return wrapper
    return decorator
