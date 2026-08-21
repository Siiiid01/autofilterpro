import pymongo
import logging
from datetime import timedelta, datetime
import pytz
import string
import random
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from info import DATABASE_URI, DATABASE_NAME, ADMINS, PREMIUM_LOGS
from utils import get_seconds, temp
import asyncio

logger = logging.getLogger(__name__)

PREMIUM_IMAGE = "https://i.ibb.co/BVLLb42X/Black-and-White-Simple-Minimalist-Special-Gift-Voucher-Certificate.jpg"

# Initialize MongoDB
myclient = pymongo.MongoClient(DATABASE_URI)
mydb = myclient[DATABASE_NAME]

class RedeemDB:
    def __init__(self):
        self.col_redeem = mydb["redeem_codes"]
        self.col_cooldown = mydb["redeem_cooldown"]
        self.col_users = mydb["users"]
        self.col_notifications = mydb["premium_notifications"]
        
        # Create indexes
        self.col_redeem.create_index("code", unique=True)
        self.col_redeem.create_index("expires_at", expireAfterSeconds=30*24*60*60)  # 30 days TTL
        self.col_cooldown.create_index("user_id", unique=True)
        self.col_notifications.create_index("notification_time")

    async def store_redeem_code(self, code: str, time: str, admin_id: int) -> bool:
        try:
            self.col_redeem.insert_one({
                "code": code,
                "time": time,
                "used_by": [],
                "created_by": admin_id,
                "created_at": datetime.now(pytz.utc),
                "active": True
            })
            return True
        except Exception as e:
            print(f"Error storing code: {e}")
            return False

    async def get_redeem_code(self, code: str):
        try:
            return self.col_redeem.find_one({"code": code, "active": True})
        except Exception as e:
            print(f"Error getting code: {e}")
            return None

    async def mark_code_used(self, code: str, user_id: int) -> bool:
        try:
            # First check if code exists and is unused
            code_data = await self.get_redeem_code(code)
            if not code_data or code_data.get('used_by'):
                return False
            
            # Update code to mark as used and deactivate it
            result = self.col_redeem.update_one(
                {
                    "code": code, 
                    "active": True,
                    "used_by": []  # Only update if no one has used it
                },
                {
                    "$set": {
                        "used_by": [user_id],
                        "active": False  # Deactivate code after use
                    }
                }
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"Error marking code used: {e}")
            return False

    async def get_user_cooldown(self, user_id: int):
        try:
            return self.col_cooldown.find_one({"user_id": user_id})
        except Exception as e:
            print(f"Error getting cooldown: {e}")
            return None

    async def set_user_cooldown(self, user_id: int) -> bool:
        try:
            cooldown_time = datetime.now(pytz.utc) + timedelta(minutes=10)
            self.col_cooldown.update_one(
                {"user_id": user_id},
                {"$set": {"cooldown_until": cooldown_time}},
                upsert=True
            )
            return True
        except Exception as e:
            print(f"Error setting cooldown: {e}")
            return False

    async def update_user_premium(self, user_id: int, expiry_time):
        try:
            self.col_users.update_one(
                {"id": user_id},
                {"$set": {"expiry_time": expiry_time}},
                upsert=True
            )
            return True
        except Exception as e:
            print(f"Error updating user premium: {e}")
            return False

    async def get_user(self, user_id: int):
        try:
            return self.col_users.find_one({"id": user_id})
        except Exception as e:
            print(f"Error getting user: {e}")
            return None

    async def list_active_codes(self):
        try:
            return list(self.col_redeem.find({"active": True}))
        except Exception as e:
            print(f"Error listing codes: {e}")
            return []

    async def revoke_code(self, code: str):
        try:
            result = self.col_redeem.update_one(
                {"code": code, "active": True},
                {"$set": {"active": False}}
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"Error revoking code: {e}")
            return False

    async def get_dashboard_stats(self):
        try:
            total = self.col_redeem.count_documents({})
            active = self.col_redeem.count_documents({"active": True})
            used = self.col_redeem.count_documents({"used_by": {"$ne": []}})
            pending = self.col_redeem.count_documents({"used_by": [], "active": True})
            revoked = self.col_redeem.count_documents({"active": False})
            
            return {
                "total": total,
                "active": active,
                "used": used,
                "pending": pending,
                "revoked": revoked
            }
        except Exception as e:
            print(f"Error getting dashboard stats: {e}")
            return None

    async def get_unused_codes(self):
        try:
            return list(self.col_redeem.find({"used_by": [], "active": True}))
        except Exception as e:
            print(f"Error getting unused codes: {e}")
            return []

    async def revoke_all_unused(self):
        try:
            result = self.col_redeem.update_many(
                {"used_by": [], "active": True},
                {"$set": {"active": False}}
            )
            return result.modified_count
        except Exception as e:
            print(f"Error revoking unused codes: {e}")
            return 0

    async def schedule_notifications(self, user_id, expiry_time):
        try:
            notifications = [
                {
                    "user_id": user_id,
                    "notification_time": expiry_time - timedelta(hours=2),
                    "type": "2hour",
                    "sent": False
                },
                {
                    "user_id": user_id,
                    "notification_time": expiry_time - timedelta(minutes=10),
                    "type": "10min",
                    "sent": False
                }
            ]
            await self.col_notifications.insert_many(notifications)
            return True
        except Exception as e:
            print(f"Error scheduling notifications: {e}")
            return False

# Initialize the database class
db = RedeemDB()

def generate_code(length=12):
    chars = string.ascii_uppercase + string.digits
    while True:
        random_part = ''.join(random.choice(chars) for _ in range(length))
        if not (set('0O1I') & set(random_part)):
            return f"ROBIN-{random_part}"

@Client.on_message(filters.command("add_redeem") & filters.user(ADMINS))
async def add_redeem_code(client, message):
    if len(message.command) != 3:
        await message.reply_text(
            "<b>♻️ Usage:</b>\n\n"
            "➜ <code>/add_redeem 1min 1</code>\n"
            "➜ <code>/add_redeem 1hour 10</code>\n"
            "➜ <code>/add_redeem 1day 5</code>"
        )
        return

    time = message.command[1]
    try:
        num_codes = int(message.command[2])
        if num_codes > 100:
            await message.reply_text("❌ Maximum 100 codes can be generated at once.")
            return
        if num_codes < 1:
            await message.reply_text("❌ Number of codes must be at least 1.")
            return
    except ValueError:
        await message.reply_text("❌ Please provide a valid number of codes.")
        return

    # Validate time format
    try:
        seconds = await get_seconds(time)
        if seconds <= 0:
            await message.reply_text("❌ Invalid time format.")
            return
    except Exception:
        await message.reply_text("❌ Invalid time format. Use format like: 1hour, 1day, etc.")
        return

    status_msg = await message.reply_text("⏳ Generating premium codes...")

    try:
        codes = []
        failed_codes = []
        for _ in range(num_codes):
            code = generate_code()
            if await db.store_redeem_code(code, time, message.from_user.id):
                codes.append(code)
            else:
                failed_codes.append(code)

        if not codes:
            await status_msg.edit_text("❌ Failed to generate any valid codes. Database error.")
            return

        if failed_codes:
            print(f"Failed to store codes: {failed_codes}")

        codes_text = '\n'.join(f"┃  🎟️ <code>/redeem {code}</code>" for code in codes)
        text = f"""
╭────────❏ PREMIUM CODES ❏───────────╮
│
│ {codes_text}                       
│                                     
│  ☃ Duration: {time}                 
│  Generated: {len(codes)}/{num_codes}
│                                     
╰──────────────────────────────────────╯

🔰 Instructions:
• Each code can be used once
• 10 minute cooldown between redeems
• Codes are case-sensitive
"""
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🔑 Redeem Now", url=f"https://t.me/{temp.U_NAME}")
        ]])
        
        await status_msg.edit_text(text, reply_markup=keyboard)
        
        # Log code generation
        if PREMIUM_LOGS:
            try:
                await client.send_message(
                    PREMIUM_LOGS,
                    f"#NEW_CODES_GENERATED\n\n"
                    f"Admin: {message.from_user.mention}\n"
                    f"Count: {num_codes}\n"
                    f"Duration: {time}\n\n"
                    f"{text}"
                )
            except Exception as e:
                print(f"Failed to log to PREMIUM_LOGS: {str(e)}")
                
    except Exception as e:
        await status_msg.edit_text(f"❌ Error generating codes: {str(e)}")

@Client.on_message(filters.command("redeem"))
async def redeem_code(client, message):
    try:
        user_id = message.from_user.id
        
        if len(message.command) != 2:
            await message.reply_text("❌ Usage: /redeem <code>")
            return

        redeem_code = message.command[1]
        
        # Check cooldown
        cooldown = await db.get_user_cooldown(user_id)
        if cooldown:
            cooldown_time = cooldown["cooldown_until"]
            if cooldown_time > datetime.now(pytz.utc):
                remaining = (cooldown_time - datetime.now(pytz.utc)).seconds
                await message.reply_text(f"⏳ Please wait {remaining//60}m {remaining%60}s before trying again.")
                return

        status_msg = await message.reply_text("⏳ Processing redemption...")

        try:
            code_data = await db.get_redeem_code(redeem_code)
        except Exception as e:
            await status_msg.edit_text(f"❌ Database error: {str(e)}")
            return
        
        if not code_data:
            await status_msg.edit_text("❌ Invalid or expired code.")
            return
            
        if user_id in code_data["used_by"]:
            await status_msg.edit_text("❌ You have already used this code.")
            return

        try:
            time = code_data["time"]
            user = await client.get_users(user_id)
            seconds = await get_seconds(time)
            
            if seconds <= 0:
                await status_msg.edit_text("❌ Invalid time format in code.")
                return

            # Check current premium status
            data = await db.get_user(user_id)
            current_expiry = data.get("expiry_time") if data else None
            now_aware = datetime.now(pytz.utc)

            if current_expiry and current_expiry.replace(tzinfo=pytz.utc) > now_aware:
                expiry_str = current_expiry.astimezone(pytz.timezone("Asia/Kolkata")).strftime("%d-%m-%Y %I:%M:%S %p")
                await status_msg.edit_text(
                    "╭─❏ PREMIUM ACTIVE ❏──╮\n"
                    f"│ Current expiry: {expiry_str} ┃\n"
                    "╰───────────────────────╯\n\n"
                    "❌ Cannot redeem while premium is active."
                )
                return

            # Activate premium
            expiry_time = now_aware + timedelta(seconds=seconds)
            await db.update_user_premium(user_id, expiry_time)
            await db.mark_code_used(redeem_code, user_id)
            await db.set_user_cooldown(user_id)

            expiry_str = expiry_time.astimezone(pytz.timezone("Asia/Kolkata")).strftime("%d-%m-%Y %I:%M:%S %p")
            success_text = f"""
╭─❏ <b>PREMIUM ACTIVATED</b> ❏──╮
│
│ 👤 <i>User:</i>{user.mention}   
│ 🆔 <i>ID:</i>`{user_id}`  
│ ⏳ <i>Duration:</i>{time}  
│ 📅 <i>Expires:</i>`{expiry_str}`  
╰───────────────────────────╯
"""
            try:
                # Send success message with image
                if PREMIUM_IMAGE:
                    await message.reply_photo(
                        photo=PREMIUM_IMAGE,
                        caption=success_text
                    )
                else:
                    await message.reply_text(success_text)
                
                await status_msg.delete()
            except Exception as e:
                await status_msg.edit_text(f"Premium activated but failed to send confirmation: {str(e)}")

            # Log redemption
            if PREMIUM_LOGS:
                try:
                    await client.send_message(
                        PREMIUM_LOGS,
                        f"#PREMIUM_ACTIVATED\n\n{success_text}"
                    )
                except Exception as e:
                    print(f"Failed to log to PREMIUM_LOGS: {str(e)}")

            # Add verification for premium activation
            try:
                # Verify user update
                await db.update_user_premium(user_id, expiry_time)
                verify_update = await db.get_user(user_id)
                if not verify_update or not verify_update.get("expiry_time"):
                    raise Exception("Failed to verify premium activation")

                # Verify code usage marking
                await db.mark_code_used(redeem_code, user_id)
                verify_code = await db.get_redeem_code(redeem_code)
                if user_id not in verify_code.get("used_by", []):
                    raise Exception("Failed to verify code usage marking")

                # Verify cooldown setting
                await db.set_user_cooldown(user_id)
                verify_cooldown = await db.get_user_cooldown(user_id)
                if not verify_cooldown:
                    raise Exception("Failed to verify cooldown setting")

            except Exception as e:
                await status_msg.edit_text(f"❌ Error verifying premium activation: {str(e)}")
                return

            # Schedule expiry notifications
            await db.schedule_notifications(user_id, expiry_time)

        except Exception as e:
            await status_msg.edit_text(f"❌ Error processing redemption: {str(e)}")

    except Exception as e:
        await message.reply_text(f"❌ An unexpected error occurred: {str(e)}")

# Admin commands
@Client.on_message(filters.command("list_codes") & filters.user(ADMINS))
async def list_codes(client, message):
    codes = await db.list_active_codes()
    if not codes:
        await message.reply_text("No active codes found.")
        return
    
    text = "┏━━━ ACTIVE CODES ━━━┓\n"
    for code in codes:
        used = len(code["used_by"])
        text += f"┃ Code: {code['code']}\n┃ Used: {used} time(s)\n┃ Duration: {code['time']}\n┃ ─────────────── ┃\n"
    text += "┗━━━━━━━━━━━━━━━━━┛"
    
    await message.reply_text(text)

@Client.on_message(filters.command("revoke_code") & filters.user(ADMINS))
async def revoke_code(client, message):
    if len(message.command) != 2:
        await message.reply_text("Usage: /revoke_code <code>")
        return
        
    code = message.command[1]
    result = await db.revoke_code(code)
    
    if result:
        await message.reply_text(f"✅ Code {code} has been revoked.")
    else:
        await message.reply_text("❌ Code not found or already revoked.")

@Client.on_message(filters.command("dashboard") & filters.user(ADMINS))
async def premium_dashboard(client, message):
    try:
        stats = await db.get_dashboard_stats()
        if not stats:
            await message.reply_text("❌ Error fetching dashboard stats")
            return

        dashboard = f"""
  PREMIUM DASHBOARD

[+] Total Generated: {stats['total']}
[+] Active Users:    {stats['active']}
[+] Used Codes:      {stats['used']}
[+] Pending Codes:   {stats['pending']}
[+] Auto-Revoked:    {stats['revoked']}
"""
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("📋 List Unused Codes", callback_data="list_unused")],
            [InlineKeyboardButton("❌ Revoke All Unused", callback_data="revoke_all")]
        ])
        
        await message.reply_text(dashboard, reply_markup=buttons)
    except Exception as e:
        await log_error(client, "Dashboard Error", str(e), message.from_user)

@Client.on_callback_query(filters.regex("^list_unused$"))
async def list_unused_codes(client, callback_query):
    try:
        codes = await db.get_unused_codes()
        if not codes:
            await callback_query.answer("No unused codes found!", show_alert=True)
            return

        text = "┏━━━━━ UNUSED CODES ━━━━━┓\n"
        for code in codes:
            created = code['created_at'].strftime("%d-%m-%Y")
            text += f"┃ Code: {code['code']}\n┃ Created: {created}\n┃ Duration: {code['time']}\n┃ ─────────────── ┃\n"
        text += "┗━━━━━━━━━━━━━━━━━━━━━┛"

        if len(text) > 4096:
            # Split into multiple messages if too long
            chunks = [text[i:i+4096] for i in range(0, len(text), 4096)]
            for chunk in chunks:
                await callback_query.message.reply_text(chunk)
        else:
            await callback_query.message.reply_text(text)
        
        await callback_query.answer()
    except Exception as e:
        await log_error(client, "List Unused Error", str(e), callback_query.from_user)

@Client.on_callback_query(filters.regex("^revoke_all$"))
async def revoke_all_codes(client, callback_query):
    try:
        confirm_buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Yes", callback_data="confirm_revoke"),
                InlineKeyboardButton("❌ No", callback_data="cancel_revoke")
            ]
        ])
        await callback_query.message.reply_text(
            "⚠️ Are you sure you want to revoke all unused codes?",
            reply_markup=confirm_buttons
        )
        await callback_query.answer()
    except Exception as e:
        await log_error(client, "Revoke All Error", str(e), callback_query.from_user)

@Client.on_callback_query(filters.regex("^confirm_revoke$"))
async def confirm_revoke_all(client, callback_query):
    try:
        count = await db.revoke_all_unused()
        await callback_query.message.reply_text(f"✅ Successfully revoked {count} unused codes.")
        await callback_query.answer()
    except Exception as e:
        await log_error(client, "Confirm Revoke Error", str(e), callback_query.from_user)

async def check_premium_notifications(bot):
    while True:
        try:
            now = datetime.now(pytz.utc)
            # Find pending notifications
            pending = db.col_notifications.find({
                "notification_time": {"$lte": now},
                "sent": False
            })

            for notification in pending:
                user_id = notification.get("user_id")
                try:
                    notification_type = notification["type"]
                    
                    text = ("⚠️ Your premium access will expire in 2 hours!" 
                           if notification_type == "2hour" 
                           else "🚨 Your premium access will expire in 10 minutes!")
                    
                    # Send new message instead of editing
                    await bot.send_message(
                        chat_id=user_id,
                        text=text
                    )
                    
                    # Mark as sent
                    db.col_notifications.update_one(
                        {"_id": notification["_id"]},
                        {"$set": {"sent": True}}
                    )
                except Exception as e:
                    logger.exception("Failed to send premium notification to user %s", user_id)
                    continue

        except Exception as e:
            logger.exception("Premium notification checker error")
        
        await asyncio.sleep(60)  # Check every minute

_notification_task = None


def start_premium_notification_checker(bot):
    """Start one notifier after the Pyrogram client has initialized."""
    global _notification_task

    if _notification_task is None or _notification_task.done():
        _notification_task = asyncio.create_task(check_premium_notifications(bot))
    return _notification_task

async def log_error(client, error_type: str, details: str, user=None):
    try:
        error_msg = f"""
#ERROR_LOG
Type: {error_type}
Time: {datetime.now(pytz.utc)}
User: {user.mention if user else 'N/A'}
Details: {details}
"""
        if PREMIUM_LOGS:
            await client.send_message(PREMIUM_LOGS, error_msg)
    except Exception as e:
        print(f"Failed to log error: {e}")
