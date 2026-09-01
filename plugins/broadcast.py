import datetime, time, os, asyncio,logging 
from pyrogram.errors import InputUserDeactivated, UserNotParticipant, FloodWait, UserIsBlocked, PeerIdInvalid
from pyrogram.errors.exceptions.bad_request_400 import MessageTooLong
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram import Client, filters, enums
from database.users_chats_db import db
from info import ADMINS, GRP_LNK
from itertools import cycle
import pytz
from utils import temp  # Add this at the top with other imports

# Loading animation frames
LOADING_CHARS = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
loading_animation = cycle(LOADING_CHARS)

def get_progress_bar(current, total, length=10):
    progress = (current / total) * length
    filled = int(progress)
    remaining = length - filled
    percent = (current / total) * 100
    return f"[{'█' * filled}{'░' * remaining}] {percent:.1f}% {next(loading_animation)}"

async def update_progress_message(message, current, total, stats):
    try:
        progress_text = get_progress_bar(current, total)
        status_text = f"""
<b>⚡ Broadcast Status</b>

<code>{progress_text}</code>

<b>💫 Progress:</b> <code>{current}/{total}</code>
<b>✅ Successful:</b> <code>{stats['successful']}</code>
<b>🚫 Blocked:</b> <code>{stats['blocked']}</code>
<b>🗑 Deleted:</b> <code>{stats['deleted']}</code>
<b>❌ Failed:</b> <code>{stats['failed']}</code>

<i>Processing...</i>
"""
        await message.edit(status_text)
    except Exception as e:
        print(f"Error updating progress: {e}")

@Client.on_message(filters.command("broadcast") & filters.user(ADMINS) & filters.reply)
async def broadcast_handler(bot, message):
    """Broadcast to all users with pin option"""
    users = await db.get_all_users()
    reply_message = message.reply_to_message
    
    if not reply_message:
        return await message.reply_text("❌ Please reply to a message to broadcast!")

    # Initialize broadcast
    start_time = datetime.datetime.now()
    status_msg = await message.reply_text("⚡ Initializing broadcast...")
    
    total_users = await db.total_users_count()
    done = 0
    successful_users = []
    stats = {
        "successful": 0,
        "blocked": 0,
        "deleted": 0,
        "failed": 0
    }

    # Process in smaller batches
    BATCH_SIZE = 4  # Reduced batch size for more frequent updates
    user_ids = []
    
    async for user in users:
        user_ids.append(user['id'])
        
        # Process when batch is full or it's the last batch
        if len(user_ids) >= BATCH_SIZE or (total_users - done) <= len(user_ids):
            tasks = [broadcast_messages(uid, reply_message) for uid in user_ids]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for user_id, result in zip(user_ids, results):
                if isinstance(result, Exception):
                    stats['failed'] += 1
                    continue
                    
                pti, sh = result
                if pti:
                    stats['successful'] += 1
                    successful_users.append(user_id)
                else:
                    if sh == "Blocked":
                        stats['blocked'] += 1
                    elif sh == "Deleted":
                        stats['deleted'] += 1
                    else:
                        stats['failed'] += 1
                
                done += 1
                
                # Update progress more frequently
                if done % 4 == 0 or done == total_users:
                    progress = (done / total_users) * 100
                    progress_bar = "".join("█" for _ in range(int(progress/10))) + "".join("░" for _ in range(10-int(progress/10)))
                    await status_msg.edit(f"""
<b>📤 Broadcasting Message...</b>

{progress_bar} {progress:.1f}%

<b>⏳ Progress:</b> {done}/{total_users}
<b>✅ Success:</b> {stats['successful']}
<b>🚫 Blocked:</b> {stats['blocked']}
<b>🗑 Deleted:</b> {stats['deleted']}
<b>❌ Failed:</b> {stats['failed']}
""")
            
            # Clear batch
            user_ids = []
            await asyncio.sleep(0.5)  # Small delay between batches

    time_taken = datetime.datetime.now() - start_time
    
    # Store context for pin option
    temp.BROADCAST_CONTEXT = {
        "successful_users": successful_users,
        "broadcast_message": reply_message
    }
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Close", callback_data="close_broadcast")]
    ])
    
    await status_msg.edit(f"""
<b>✅ Broadcast Completed!</b>

[██████████] 100% ✓

<b>⏰ Time Taken:</b> {time_taken.seconds} seconds
<b>👥 Total Users:</b> {total_users}
<b>✅ Successful:</b> {stats['successful']}
<b>🚫 Blocked:</b> {stats['blocked']}
<b>🗑 Deleted:</b> {stats['deleted']}
<b>❌ Failed:</b> {stats['failed']}

<i>Use buttons below to close this message.</i>
""", reply_markup=buttons)

@Client.on_callback_query(filters.regex("^close_broadcast"))
async def close_broadcast_callback(bot, query):
    try:
        await query.message.delete()
    except Exception as e:
        print(f"Error closing broadcast message: {str(e)}")

@Client.on_message(filters.command("groupcast") & filters.user(ADMINS) & filters.reply)
async def group_broadcast(bot, message):
    """Broadcast to all groups"""
    chats = await db.get_all_chats()
    reply_message = message.reply_to_message
    
    if not reply_message:
        return await message.reply_text("❌ Please reply to a message to broadcast!")

    # Initialize broadcast
    start_time = datetime.datetime.now()
    status_msg = await message.reply_text("⚡ Initializing group broadcast...")
    
    total_chats = await db.total_chat_count()
    done = 0
    stats = {
        "successful": 0,
        "blocked": 0,
        "deleted": 0,
        "failed": 0
    }
    errors = []  # Store errors for logging
    
    async for chat in chats:
        try:
            pti, sh = await broadcast_messages(int(chat['id']), reply_message, None)
            if pti:
                stats['successful'] += 1
            else:
                if sh == "Deleted/Blocked":
                    stats['deleted'] += 1
                    errors.append(f"Chat {chat['id']}: Deleted/Blocked")
                else:
                    stats['failed'] += 1
                    errors.append(f"Chat {chat['id']}: {sh}")
            
            done += 1
            if not done % 4:
                await update_progress_message(status_msg, done, total_chats, stats)
                
        except Exception as e:
            stats['failed'] += 1
            print(f"Group Broadcast Error: {e}")
        
        await asyncio.sleep(0.1)

    time_taken = datetime.datetime.now() - start_time
    
    # If there are errors, log them
    if errors:
        error_text = "\n".join(errors)
        await log_error(bot, error_text, message.from_user.id)

    final_status = f"""
<b>✅ Group Broadcast Completed!</b>

[██████████] 100% ✓

<b>⏰ Time Taken:</b> <code>{time_taken.seconds} seconds</code>
<b>👥 Total Groups:</b> <code>{total_chats}</code>
<b>✅ Successful:</b> <code>{stats['successful']}</code>
<b>🗑 Deleted:</b> <code>{stats['deleted']}</code>
<b>❌ Failed:</b> <code>{stats['failed']}</code>
"""
    await status_msg.edit(final_status)

@Client.on_message(filters.command("clear_junk") & filters.user(ADMINS))
async def remove_junkuser__db(bot, message):
    users = await db.get_all_users()
    b_msg = message 
    sts = await message.reply_text('<i>In Progress...</i>')   
    start_time = time.time()
    total_users = await db.total_users_count()
    blocked = 0
    deleted = 0
    failed = 0
    done = 0
    async for user in users:
        pti, sh = await clear_junk(int(user['id']), b_msg)
        if pti == False:
            if sh == "Blocked":
                blocked+=1
            elif sh == "Deleted":
                deleted += 1
            elif sh == "Error":
                failed += 1
        done += 1
        if not done % 4:
            await sts.edit(f"In Progress:\n\nTotal Users {total_users}\nCompleted: {done} / {total_users}\nBlocked: {blocked}\nDeleted: {deleted}")    
    time_taken = datetime.timedelta(seconds=int(time.time()-start_time))
    await sts.delete()
    await bot.send_message(message.chat.id, f"Completed:\nCompleted in {time_taken} seconds.\n\nTotal Users {total_users}\nCompleted: {done} / {total_users}\nBlocked: {blocked}\nDeleted: {deleted}")


# @Client.on_message(filters.command("grp_broadcast") & filters.user(ADMINS) & filters.reply)
# async def broadcast_group(bot, message):
#     groups = await db.get_all_chats()
#     if not groups:
#         grp = await message.reply_text("❌ Nᴏ ɢʀᴏᴜᴘs ғᴏᴜɴᴅ ғᴏʀ ʙʀᴏᴀᴅᴄᴀsᴛɪɴɢ.")
#         await asyncio.sleep(60)
#         await grp.delete()
#         return
#     b_msg = message.reply_to_message
#     sts = await message.reply_text(text='Bʀᴏᴀᴅᴄᴀsᴛɪɴɢ ʏᴏᴜʀ ᴍᴇssᴀɢᴇs Tᴏ Gʀᴏᴜᴘs...')
#     start_time = time.time()
#     total_groups = await db.total_chat_count()
#     done = 0
#     failed = ""
#     success = 0
#     deleted = 0
#     async for group in groups:
#         pti, sh, ex = await broadcast_messages_group(int(group['id']), b_msg)
#         if pti == True:
#             if sh == "Succes":
#                 success += 1
#         elif pti == False:
#             if sh == "deleted":
#                 deleted+=1 
#                 failed += ex 
#                 try:
#                     await bot.leave_chat(int(group['id']))
#                 except Exception as e:
#                     print(f"{e} > {group['id']}")  
#         done += 1
#         if not done % 20:
#             await sts.edit(f"Broadcast in progress:\n\nTotal Groups {total_groups}\nCompleted: {done} / {total_groups}\nSuccess: {success}\nDeleted: {deleted}")    
#     time_taken = datetime.timedelta(seconds=int(time.time()-start_time))
#     await sts.delete()
#     try:
#         await message.reply_text(f"Broadcast Completed:\nCompleted in {time_taken} seconds.\n\nTotal Groups {total_groups}\nCompleted: {done} / {total_groups}\nSuccess: {success}\nDeleted: {deleted}\n\nFiled Reson:- {failed}")
#     except MessageTooLong:
#         with open('reason.txt', 'w+') as outfile:
#             outfile.write(failed)
#         await message.reply_document('reason.txt', caption=f"Completed:\nCompleted in {time_taken} seconds.\n\nTotal Groups {total_groups}\nCompleted: {done} / {total_groups}\nSuccess: {success}\nDeleted: {deleted}")
#         os.remove("reason.txt")

      
@Client.on_message(filters.command(["junk_group", "clear_junk_group"]) & filters.user(ADMINS))
async def junk_clear_group(bot, message):
    groups = await db.get_all_chats()
    if not groups:
        grp = await message.reply_text("❌ Nᴏ ɢʀᴏᴜᴘs ғᴏᴜɴᴅ ғᴏʀ ᴄʟᴇᴀʀ Jᴜɴᴋ ɢʀᴏᴜᴘs.")
        await asyncio.sleep(60)
        await grp.delete()
        return
    b_msg = message
    sts = await message.reply_text(text='..............')
    start_time = time.time()
    total_groups = await db.total_chat_count()
    done = 0
    failed = ""
    deleted = 0
    async for group in groups:
        pti, sh, ex = await junk_group(int(group['id']), b_msg)        
        if pti == False:
            if sh == "deleted":
                deleted+=1 
                failed += ex 
                try:
                    await bot.leave_chat(int(group['id']))
                except Exception as e:
                    print(f"{e} > {group['id']}")  
        done += 1
        if not done % 4:
            await sts.edit(f"in progress:\n\nTotal Groups {total_groups}\nCompleted: {done} / {total_groups}\nDeleted: {deleted}")    
    time_taken = datetime.timedelta(seconds=int(time.time()-start_time))
    await sts.delete()
    try:
        await bot.send_message(message.chat.id, f"Completed:\nCompleted in {time_taken} seconds.\n\nTotal Groups {total_groups}\nCompleted: {done} / {total_groups}\nDeleted: {deleted}\n\nFiled Reson:- {failed}")    
    except MessageTooLong:
        with open('junk.txt', 'w+') as outfile:
            outfile.write(failed)
        await message.reply_document('junk.txt', caption=f"Completed:\nCompleted in {time_taken} seconds.\n\nTotal Groups {total_groups}\nCompleted: {done} / {total_groups}\nDeleted: {deleted}")
        os.remove("junk.txt")

async def broadcast_messages_group(chat_id, message):
    try:
        await message.copy(chat_id=chat_id)
        return True, "Succes", 'mm'
    except FloodWait as e:
        await asyncio.sleep(e.value)
        return await broadcast_messages_group(chat_id, message)
    except Exception as e:
        await db.delete_chat(int(chat_id))       
        logging.info(f"{chat_id} - PeerIdInvalid")
        return False, "deleted", f'{e}\n\n'
    
async def junk_group(chat_id, message):
    try:
        kk = await message.copy(chat_id=chat_id)
        await kk.delete(True)
        return True, "Succes", 'mm'
    except FloodWait as e:
        await asyncio.sleep(e.value)
        return await junk_group(chat_id, message)
    except Exception as e:
        await db.delete_chat(int(chat_id))       
        logging.info(f"{chat_id} - PeerIdInvalid")
        return False, "deleted", f'{e}\n\n'
    

async def clear_junk(user_id, message):
    try:
        key = await message.copy(chat_id=user_id)
        await key.delete(True)
        return True, "Success"
    except FloodWait as e:
        await asyncio.sleep(e.value)
        return await clear_junk(user_id, message)
    except InputUserDeactivated:
        await db.delete_user(int(user_id))
        logging.info(f"{user_id}-Removed from Database, since deleted account.")
        return False, "Deleted"
    except UserIsBlocked:
        logging.info(f"{user_id} -Blocked the bot.")
        return False, "Blocked"
    except PeerIdInvalid:
        await db.delete_user(int(user_id))
        logging.info(f"{user_id} - PeerIdInvalid")
        return False, "Error"
    except Exception as e:
        return False, "Error"

async def broadcast_messages(user_id, message, reply_markup=None):
    try:
        await message.copy(chat_id=user_id,reply_markup=reply_markup)
        return True, "Success"
    except FloodWait as e:
        await asyncio.sleep(e.value)
        return await broadcast_messages(user_id, message,reply_markup=reply_markup)
    except InputUserDeactivated:
        await db.delete_user(int(user_id))
        logging.info(f"{user_id}-Removed from Database, since deleted account.")
        return False, "Deleted"
    except UserIsBlocked:
        logging.info(f"{user_id} -Blocked the bot.")
        return False, "Blocked"
    except PeerIdInvalid:
        await db.delete_user(int(user_id))
        logging.info(f"{user_id} - PeerIdInvalid")
        return False, "Error"
    except Exception as e:
        return False, "Error"

async def log_error(bot, error_text: str, user_id: int):
    """Log errors and send to admin"""
    try:
        # Create error log file
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"error_log_{timestamp}.txt"
        
        with open(filename, "w") as f:
            f.write(f"Error Time: {datetime.datetime.now()}\n")
            f.write(f"User ID: {user_id}\n")
            f.write(f"Error Details:\n{error_text}")
            
        # Send file to admin
        for admin in ADMINS:
            try:
                await bot.send_document(
                    chat_id=admin,
                    document=filename,
                    caption="❌ Broadcast Error Log"
                )
            except Exception as e:
                print(f"Failed to send error log to admin {admin}: {e}")
                
        # Clean up file
        os.remove(filename)
        
    except Exception as e:
        print(f"Error in error logging: {e}")
