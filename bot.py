from pyrogram import Client, idle, __version__
import patch
from pyrogram.raw.all import layer
import logging
import logging.config
import time
import asyncio
from datetime import date, datetime
import pytz
from aiohttp import web

from database.ia_filterdb import Media, Media2, choose_mediaDB, tempDict, db as clientDB
from database.users_chats_db import db
from info import *
from utils import temp
from Script import script
from plugins import web_server, check_expired_premium
from LucyBot.Bot import Codeflix
from LucyBot.util.keepalive import ping_server
from LucyBot.Bot.clients import initialize_clients

logging.config.fileConfig('logging.conf')
logging.getLogger().setLevel(logging.INFO)
logging.getLogger("pyrogram").setLevel(logging.ERROR)
logging.getLogger("imdbpy").setLevel(logging.ERROR)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logging.getLogger("aiohttp").setLevel(logging.ERROR)
logging.getLogger("aiohttp.web").setLevel(logging.ERROR)

botStartTime = time.time()

async def check_expired_temporary_bans():
    while True:
        expired_user_ids = await db.expire_temporary_bans()
        for user_id in expired_user_ids:
            if user_id in temp.BANNED_USERS:
                temp.BANNED_USERS.remove(user_id)
        await asyncio.sleep(30)

async def Lucy_start():
    try:
        print('\n')
        print('\nInitalizing Lucy')
        await Codeflix.start()
        from plugins.Extra.Redeem import start_premium_notification_checker
        start_premium_notification_checker(Codeflix)
        bot_info = await Codeflix.get_me()
        Codeflix.username = bot_info.username
        await initialize_clients()
        if ON_HEROKU:
            asyncio.create_task(ping_server()) 
        b_users, b_chats = await db.get_banned()
        temp.BANNED_USERS = b_users
        temp.BANNED_CHATS = b_chats
        asyncio.create_task(check_expired_temporary_bans())
        await Media.ensure_indexes()
        await Media2.ensure_indexes()
        stats = await clientDB.command('dbStats')
        free_dbSize = round(512-((stats['dataSize']/(1024*1024))+(stats['indexSize']/(1024*1024))), 2)
        if DATABASE_URI2 and free_dbSize<62: #if the primary db have less than 62MB left, use second DB.
            tempDict["indexDB"] = DATABASE_URI2
            logging.info(f"Since Primary DB have only {free_dbSize} MB left, Secondary DB will be used to store datas.")
        elif DATABASE_URI2 is None:
            logging.error("Missing second DB URI !\n\nAdd SECONDDB_URI now !\n\nExiting...")
            exit()
        else:
            logging.info(f"Since primary DB have enough space ({free_dbSize}MB) left, It will be used for storing datas.")
        await choose_mediaDB()    
        me = await Codeflix.get_me()
        temp.ME = me.id
        temp.U_NAME = me.username
        temp.B_NAME = me.first_name
        temp.B_LINK = me.mention
        Codeflix.username = '@' + me.username
        # Reload pending verification tokens from MongoDB into memory (survives restarts)
        try:
            loaded_tokens = await db.load_all_verify_tokens()
            temp.VERIFY_LINKS.update(loaded_tokens)
            if loaded_tokens:
                logging.info(f"Reloaded {len(loaded_tokens)} pending verification token(s) from DB.")
        except Exception as e:
            logging.warning(f"Could not reload verify tokens: {e}")
        Codeflix.loop.create_task(check_expired_premium(Codeflix))
        logging.info(f"{me.first_name} with Pyrogram v{__version__} (Layer {layer}) started on {me.username}.")
        logging.info(LOG_STR)
        logging.info(script.LOGO)
        tz = pytz.timezone('Asia/Kolkata')
        today = date.today()
        now = datetime.now(tz)
        time_str = now.strftime("%H:%M:%S %p")
        await Codeflix.send_message(chat_id=LOG_CHANNEL, text=script.RESTART_TXT.format(temp.B_LINK, today, time_str))
        app = web.AppRunner(await web_server())
        await app.setup()
        bind_address = "0.0.0.0"
        await web.TCPSite(app, bind_address, PORT).start()
        await idle()
    except Exception as e:
        import traceback
        logging.error(f"[ERROR] Startup failure: {e}\n{traceback.format_exc()}")
        exit(1)
if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(Lucy_start())
    except KeyboardInterrupt:
        logging.info('Service Stopped Bye 👋')
