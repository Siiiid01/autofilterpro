import re
from pyrogram import filters, Client, enums
from pyrogram.errors.exceptions.bad_request_400 import ChannelInvalid, UsernameInvalid, UsernameNotModified
from info import ADMINS, LOG_CHANNEL, FILE_STORE_CHANNEL, PUBLIC_FILE_STORE
from database.ia_filterdb import unpack_new_file_id, save_file
from utils import temp
import re
import os
import json
import base64
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

async def allowed(_, __, message):
    if PUBLIC_FILE_STORE:
        return True
    if message.from_user and message.from_user.id in ADMINS:
        return True
    return False

@Client.on_message(filters.command(['link', 'plink']) & filters.create(allowed))
async def gen_link_s(bot, message):
    replied = message.reply_to_message
    if not replied:
        return await message.reply('Reply to a message to get a shareable link.')
    file_type = replied.media
    if file_type not in [enums.MessageMediaType.VIDEO, enums.MessageMediaType.AUDIO, enums.MessageMediaType.DOCUMENT, enums.MessageMediaType.PHOTO]:
        if file_type is None:
            # It's a text message
            is_plink = message.command[0].lower() == "plink"
            post = await replied.copy(LOG_CHANNEL)
            cmd_type = "/pbatch" if is_plink else "/batch"
            string = f"{post.id}_{post.id}_{LOG_CHANNEL}_{cmd_type}"
            b_64 = base64.urlsafe_b64encode(string.encode("ascii")).decode().strip("=")
            return await message.reply(
                f"Here is your Link:\nhttps://t.me/{temp.U_NAME}?start=DSTORE-{b_64}",
                parse_mode=enums.ParseMode.HTML
            )
        elif message.from_user and message.from_user.id in ADMINS:
            is_plink = message.command[0].lower() == "plink"
            post = await replied.copy(LOG_CHANNEL)
            cmd_type = "/pbatch" if is_plink else "/batch"
            string = f"{post.id}_{post.id}_{LOG_CHANNEL}_{cmd_type}"
            b_64 = base64.urlsafe_b64encode(string.encode("ascii")).decode().strip("=")
            return await message.reply(
                f"Here is your Link (Special Admin Mode):\nhttps://t.me/{temp.U_NAME}?start=DSTORE-{b_64}",
                parse_mode=enums.ParseMode.HTML
            )
        else:
            return await message.reply("Reply to a supported media")
            
    if message.has_protected_content and message.chat.id not in ADMINS:
        return await message.reply("okDa")

    is_plink = message.command[0].lower() == "plink"
    media = getattr(replied, file_type.value)
    file_id, ref = unpack_new_file_id(media.file_id)
    string = 'filep_' if is_plink else 'file_'
    string += file_id
    outstr = base64.urlsafe_b64encode(string.encode("ascii")).decode().strip("=")

    if is_plink:
        # Save file permanently to MongoDB so the link survives bot restarts
        media.file_type = file_type.value
        media.caption = replied.caption
        saved, status = await save_file(bot, media)
        if saved:
            db_note = "\n\n✅ <b>File saved to database</b> — link is permanent."
        elif status == 0:
            db_note = "\n\n♻️ <b>File already in database</b> — link is permanent."
        else:
            db_note = "\n\n⚠️ <b>Could not save to database</b> — link may expire."
    else:
        db_note = ""

    await message.reply(
        f"Here is your Link:\nhttps://t.me/{temp.U_NAME}?start={outstr}{db_note}",
        parse_mode=enums.ParseMode.HTML
    )
    
    
@Client.on_message(filters.command(['batch', 'pbatch']) & filters.create(allowed))
async def gen_link_batch(bot, message):
    if " " not in message.text:
        return await message.reply("Use correct format.\nExample <code>/batch https://t.me/WilsonVerse/10 https://t.me/WilsonVerse/20</code>.")
    links = message.text.strip().split(" ")
    if len(links) != 3:
        return await message.reply("Use correct format.\nExample <code>/batch https://t.me/WilsonVerse/10 https://t.me/WilsonVerse/20</code>.")
    cmd, first, last = links
    regex = re.compile(r"(https://)?(t\.me/|telegram\.me/|telegram\.dog/)(c/)?(\d+|[a-zA-Z_0-9]+)/(\d+)$")
    match = regex.match(first)
    if not match:
        return await message.reply('Invalid link')
    f_chat_id = match.group(4)
    f_msg_id = int(match.group(5))
    if f_chat_id.isnumeric():
        f_chat_id  = int(("-100" + f_chat_id))

    match = regex.match(last)
    if not match:
        return await message.reply('Invalid link')
    l_chat_id = match.group(4)
    l_msg_id = int(match.group(5))
    if l_chat_id.isnumeric():
        l_chat_id  = int(("-100" + l_chat_id))

    if f_chat_id != l_chat_id:
        return await message.reply("Chat ids not matched.")
    try:
        chat_id = (await bot.get_chat(f_chat_id)).id
    except ChannelInvalid:
        return await message.reply('This may be a private channel / group. Make me an admin over there to index the files.')
    except (UsernameInvalid, UsernameNotModified):
        return await message.reply('Invalid Link specified.')
    except Exception as e:
        return await message.reply(f'Errors - {e}')

    is_pbatch = cmd.lower().strip() in ["/pbatch", "pbatch"]

    sts = await message.reply("Generating link for your message.\nThis may take time depending upon number of messages")

    # DSTORE fast-path: only for /batch (not /pbatch — pbatch always saves to DB)
    if chat_id in FILE_STORE_CHANNEL and not is_pbatch:
        string = f"{f_msg_id}_{l_msg_id}_{chat_id}_{cmd.lower().strip()}"
        b_64 = base64.urlsafe_b64encode(string.encode("ascii")).decode().strip("=")
        return await sts.edit(f"Here is your link https://t.me/{temp.U_NAME}?start=DSTORE-{b_64}")

    FRMT = "Generating Link...\nTotal Messages: `{total}`\nDone: `{current}`\nRemaining: `{rem}`\nStatus: `{sts}`"

    outlist = []
    og_msg = 0
    tot = 0
    async for msg in bot.iter_messages(f_chat_id, l_msg_id, f_msg_id):
        tot += 1
        if msg.empty or msg.service:
            continue
        if not msg.media:
            # only media messages supported.
            continue
        try:
            file_type = msg.media
            if file_type not in [enums.MessageMediaType.VIDEO, enums.MessageMediaType.AUDIO, enums.MessageMediaType.DOCUMENT]:
                continue
            file = getattr(msg, file_type.value)
            caption = getattr(msg, 'caption', '')
            if caption:
                caption = caption.html
            if file:
                if is_pbatch:
                    # Save each file to MongoDB permanently
                    file.file_type = file_type.value
                    file.caption = msg.caption
                    await save_file(bot, file)
                    # Use the DB-unpacked file_id so resolution always goes through DB
                    db_file_id, _ = unpack_new_file_id(file.file_id)
                else:
                    db_file_id = file.file_id

                file_data = {
                    "file_id": db_file_id,
                    "caption": caption,
                    "title": getattr(file, "file_name", ""),
                    "size": file.file_size,
                    "protect": is_pbatch,
                }
                og_msg += 1
                outlist.append(file_data)
        except:
            pass
        if og_msg and not og_msg % 20:
            try:
                await sts.edit(FRMT.format(total=l_msg_id-f_msg_id, current=tot, rem=((l_msg_id-f_msg_id) - tot), sts="Saving to DB..." if is_pbatch else "Saving Messages"))
            except:
                pass
    with open(f"batchmode_{message.from_user.id}.json", "w+") as out:
        json.dump(outlist, out)
    post = await bot.send_document(LOG_CHANNEL, f"batchmode_{message.from_user.id}.json", file_name="Batch.json", caption="⚠️Generated for filestore.")
    os.remove(f"batchmode_{message.from_user.id}.json")
    file_id, ref = unpack_new_file_id(post.document.file_id)
    db_suffix = " (📦 files saved to DB — permanent)" if is_pbatch else ""
    await sts.edit(f"Here is your link\nContains `{og_msg}` files.{db_suffix}\n https://t.me/{temp.U_NAME}?start=BATCH-{file_id}")
