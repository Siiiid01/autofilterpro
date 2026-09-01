import motor.motor_asyncio
from info import *
import datetime
import pytz  
from pymongo.errors import DuplicateKeyError
from pymongo import MongoClient, ReturnDocument

async_client = motor.motor_asyncio.AsyncIOMotorClient(DATABASE_URI)
mydb = async_client["filename"]

async def add_name(user_id, filename):
    user_db = mydb[str(user_id)]
    user = {'_id': filename}
    existing_user = await user_db.find_one({'_id': filename})
    if existing_user is not None:
        return False
    try:
        await user_db.insert_one(user)
        return True
    except DuplicateKeyError:
        return False
      
async def delete_all_msg(user_id):
    user_db = mydb[str(user_id)]
    await user_db.delete_many({})


class Database:
    
    def __init__(self, uri, database_name):
        self._client = motor.motor_asyncio.AsyncIOMotorClient(uri)
        self.db = self._client[database_name]
        self.col = self.db.users
        self.grp = self.db.groups
        self.users = self.db.users
        self.req = self.db.requests
        self.botcol = self.db["deendayal"]  
        self.bot_id_col = self.db["bot_id"]
        self.verify_tokens = self.db["verify_tokens"]  # Persistent verification tokens

    async def find_join_req(self, id):
        return bool(await self.req.find_one({'id': id})) 
     
    async def add_join_req(self, id):
        await self.req.insert_one({'id': id})

    async def del_join_req(self):
        await self.req.drop()

    def new_user(self, id, name):
        return dict(
            id = id,
            name = name,
            ban_status=dict(
                is_banned=False,
                ban_reason="",
            ),
            shortlink_bypass=dict(
                warnings=0,
                last_detected_at=None,
            ),
        )

    def new_group(self, id, title):
        return dict(
            id = id,
            title = title,
            chat_status=dict(
                is_disabled=False,
                reason="",
            ),
        )

    # ============================
    # Verify Token Persistence
    # ============================
    async def save_verify_token(self, token: str, data: dict):
        """Persist a pending verification token to MongoDB."""
        doc = {
            '_id': token,
            'user_id': int(data['user_id']),
            'file_id': str(data['file_id']),
            'issued_at': data['issued_at'],
            'expires_at': data['issued_at'] + datetime.timedelta(hours=VERIFY_EXPIRE + 1),
        }
        await self.verify_tokens.replace_one({'_id': token}, doc, upsert=True)

    async def delete_verify_token(self, token: str):
        """Remove a consumed or invalidated token from MongoDB."""
        await self.verify_tokens.delete_one({'_id': token})

    async def load_all_verify_tokens(self) -> dict:
        """Load all non-expired tokens from MongoDB into memory on startup."""
        now = datetime.datetime.now(datetime.timezone.utc)
        result = {}
        async for doc in self.verify_tokens.find({'expires_at': {'$gt': now}}):
            token = doc['_id']
            issued = doc['issued_at']
            if issued.tzinfo is None:
                issued = issued.replace(tzinfo=datetime.timezone.utc)
            result[token] = {
                'user_id': int(doc['user_id']),
                'file_id': str(doc['file_id']),
                'issued_at': issued,
            }
        # Clean up expired tokens
        await self.verify_tokens.delete_many({'expires_at': {'$lte': now}})
        return result

    # ============================
    # Verification Status
    # ============================
    async def update_verification(self, id, date, time):
        status = {
            'date': str(date),
            'time': str(time)
        }
        await self.col.update_one({'id': int(id)}, {'$set': {'verification_status': status}})

    async def get_verified(self, id):
        default = {
            'date': "1999-12-31",
            'time': "23:59:59"
        }
        user = await self.col.find_one({'id': int(id)})
        if user:
            return user.get("verification_status", default)
        return default    
    
    async def add_user(self, id, name):
        user = self.new_user(id, name)
        await self.col.insert_one(user)
    
    async def is_user_exist(self, id):
        user = await self.col.find_one({'id':int(id)})
        return bool(user)
    
    async def total_users_count(self):
        count = await self.col.count_documents({})
        return count
    
    async def remove_ban(self, id):
        ban_status = dict(
            is_banned=False,
            ban_reason=''
        )
        await self.col.update_one({'id': id}, {'$set': {'ban_status': ban_status}})
    
    async def ban_user(self, user_id, ban_reason="No Reason", duration_hours=None):
        ban_status = dict(
            is_banned=True,
            ban_reason=ban_reason
        )
        if duration_hours is not None:
            ban_status['banned_until'] = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=duration_hours)
        await self.col.update_one({'id': user_id}, {'$set': {'ban_status': ban_status}})
        return ban_status

    async def get_ban_status(self, id):
        default = dict(
            is_banned=False,
            ban_reason=''
        )
        user = await self.col.find_one({'id':int(id)})
        if not user:
            return default
        ban_status = user.get('ban_status', default)
        banned_until = ban_status.get('banned_until')
        if ban_status.get('is_banned') and banned_until and banned_until.replace(tzinfo=datetime.timezone.utc) <= datetime.datetime.now(datetime.timezone.utc):
            await self.remove_ban(int(id))
            return default
        return ban_status

    async def record_shortlink_bypass(self, user_id):
        """Record a too-fast verification attempt and return its warning number."""
        user = await self.col.find_one_and_update(
            {'id': int(user_id)},
            {
                '$inc': {'shortlink_bypass.warnings': 1},
                '$set': {'shortlink_bypass.last_detected_at': datetime.datetime.now(datetime.timezone.utc)},
            },
            return_document=ReturnDocument.AFTER,
        )
        return user.get('shortlink_bypass', {}).get('warnings', 1) if user else 1

    async def expire_temporary_bans(self):
        """Remove expired shortlink-bypass bans and return the affected user IDs."""
        now = datetime.datetime.now(datetime.timezone.utc)
        query = {
            'ban_status.is_banned': True,
            'ban_status.banned_until': {'$exists': True, '$ne': None, '$lte': now},
        }
        expired_ids = [user['id'] async for user in self.col.find(query, {'id': 1})]
        if expired_ids:
            await self.col.update_many(
                {'id': {'$in': expired_ids}},
                {'$set': {'ban_status': {'is_banned': False, 'ban_reason': ''}}},
            )
        return expired_ids

    async def get_all_users(self):
        return self.col.find({})
    
    async def delete_user(self, user_id):
        await self.col.delete_many({'id': int(user_id)})
        
    async def delete_chat(self, id):
        await self.grp.delete_many({'id': int(id)})    

    async def get_banned(self):
        await self.expire_temporary_bans()
        users = self.col.find({'ban_status.is_banned': True})
        chats = self.grp.find({'chat_status.is_disabled': True})
        b_chats = [chat['id'] async for chat in chats]
        b_users = [user['id'] async for user in users]
        return b_users, b_chats
    
    async def add_chat(self, chat, title):
        chat = self.new_group(chat, title)
        await self.grp.insert_one(chat)
    
    async def get_chat(self, chat):
        chat = await self.grp.find_one({'id':int(chat)})
        return False if not chat else chat.get('chat_status')
    
    async def re_enable_chat(self, id):
        chat_status=dict(
            is_disabled=False,
            reason="",
            )
        await self.grp.update_one({'id': int(id)}, {'$set': {'chat_status': chat_status}})
        
    async def update_settings(self, id, settings):
        await self.grp.update_one({'id': int(id)}, {'$set': {'settings': settings}})
            
    async def get_settings(self, id):
        default = {
            'button': SINGLE_BUTTON,
            'botpm': P_TTI_SHOW_OFF,
            'file_secure': PROTECT_CONTENT,
            'imdb': IMDB,
            'spell_check': SPELL_CHECK_REPLY,
            'welcome': MELCOW_NEW_USERS,
            'auto_delete': AUTO_DELETE,
            'auto_ffilter': AUTO_FFILTER,
            'max_btn': MAX_BTN,
            'template': IMDB_TEMPLATE,
            'shortlink': SHORTLINK_URL,
            'shortlink_api': SHORTLINK_API,
            'is_shortlink': IS_SHORTLINK,
            'tutorial': TUTORIAL,
            'is_tutorial': IS_TUTORIAL,
            'is_verify': VERIFY,
            'fsub': MULTI_FSUB,
        }
        chat = await self.grp.find_one({'id':int(id)})
        if chat:
            return chat.get('settings', default)
        return default
    
    async def disable_chat(self, chat, reason="No Reason"):
        chat_status=dict(
            is_disabled=True,
            reason=reason,
            )
        await self.grp.update_one({'id': int(chat)}, {'$set': {'chat_status': chat_status}})

    async def total_chat_count(self):
        count = await self.grp.count_documents({})
        return count
    
    async def get_all_chats(self):
        return self.grp.find({})

    async def get_db_size(self):
        return (await self.db.command("dbstats"))['dataSize']

    async def get_user(self, user_id):
        user_data = await self.users.find_one({"id": user_id})
        return user_data

    async def update_user(self, user_data):
        await self.users.update_one({"id": user_data["id"]}, {"$set": user_data}, upsert=True)

    async def has_premium_access(self, user_id):
        user_data = await self.get_user(user_id)
        if user_data:
            expiry_time = user_data.get("expiry_time")
            if expiry_time is None:
                return False
            elif isinstance(expiry_time, datetime.datetime) and datetime.datetime.now() <= expiry_time:
                return True
            else:
                await self.users.update_one({"id": user_id}, {"$set": {"expiry_time": None}})
        return False

    async def update_one(self, filter_query, update_data):
        try:
            result = await self.users.update_one(filter_query, update_data)
            return result.matched_count == 1
        except Exception as e:
            print(f"Error updating document: {e}")
            return False

    async def get_expired(self, current_time):
        expired_users = []
        if data := self.users.find({"expiry_time": {"$lt": current_time}}):
            async for user in data:
                expired_users.append(user)
        return expired_users

    async def remove_premium_access(self, user_id):
        return await self.update_one(
            {"id": user_id}, {"$set": {"expiry_time": None}}
        )

    async def check_trial_status(self, user_id):
        user_data = await self.get_user(user_id)
        if user_data:
            return user_data.get("has_free_trial", False)
        return False

    async def give_free_trial(self, user_id):
        seconds = 5*60         
        expiry_time = datetime.datetime.now() + datetime.timedelta(seconds=seconds)
        user_data = {"id": user_id, "expiry_time": expiry_time, "has_free_trial": True}
        await self.users.update_one({"id": user_id}, {"$set": user_data}, upsert=True)

    async def all_premium_users(self):
        count = await self.users.count_documents({
        "expiry_time": {"$gt": datetime.datetime.now()}
        })
        return count
    
    async def get_bot_setting(self, bot_id, setting_key, default_value):
        bot = await self.botcol.find_one({'id': int(bot_id)}, {setting_key: 1, '_id': 0})
        return bot[setting_key] if bot and setting_key in bot else default_value

    async def update_bot_setting(self, bot_id, setting_key, value):
        await self.botcol.update_one(
            {'id': int(bot_id)}, 
            {'$set': {setting_key: value}}, 
            upsert=True
        )

    async def pm_search_status(self, bot_id):
        return await self.get_bot_setting(bot_id, 'PM_SEARCH', PM_SEARCH)

    async def update_pm_search_status(self, bot_id, enable):
        await self.update_bot_setting(bot_id, 'PM_SEARCH', enable)

    async def movie_update_status(self, bot_id):
        return await self.get_bot_setting(bot_id, 'MOVIE_UPDATE_NOTIFICATION', MOVIE_UPDATE_NOTIFICATION)

    async def update_movie_update_status(self, bot_id, enable):
        await self.update_bot_setting(bot_id, 'MOVIE_UPDATE_NOTIFICATION', enable)

        
db = Database(DATABASE_URI, DATABASE_NAME)
db2 = Database(DATABASE_URI2, DATABASE_NAME) if DATABASE_URI2 else None
