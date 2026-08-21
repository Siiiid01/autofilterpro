import re
import os
from os import environ, getenv
from Script import script
import random

# Utility functions
id_pattern = re.compile(r'^-?\d+$')

def is_enabled(value, default):
    if value.lower() in ["true", "yes", "1", "enable", "y"]:
        return True
    elif value.lower() in ["false", "no", "0", "disable", "n"]:
        return False
    else:
        return default

# ============================
# Bot Information Configuration
# ============================
SESSION = environ.get('SESSION', 'quirky2')
API_ID = int(environ.get('API_ID', ''))
API_HASH = environ.get('API_HASH', '')
BOT_TOKEN = environ.get('BOT_TOKEN', "")

# ============================
# Bot Settings Configuration
# ============================
CACHE_TIME = int(environ.get('CACHE_TIME', 300))
USE_CAPTION_FILTER = bool(environ.get('USE_CAPTION_FILTER', True))

PICS = (environ.get('PICS', 'https://i.ibb.co/wNcsWpYB/0abea8b13af0f2d75151920ae7ffaf7f.jpg https://i.ibb.co/4ncynXpB/3c6ed16e27c02627d49f6cdd991e02fb.jpg https://i.ibb.co/j9s7Jtbk/3d9cd65506d6362479ef1bd6d3cb942f.jpg https://i.ibb.co/60F9DSNF/6d42c13ef9b3e693f7b4cb2ca1f565b3.jpg https://i.ibb.co/7tKcQFD8/6e70f9ced988b5cda4166d4c68d2a149.jpg https://i.ibb.co/XZn0p1C0/7a1d3707ec16e1a7c8aa2220b89a1e9f.jpg https://i.ibb.co/s9gPmpy8/7ceef91432bacfea46925b11751b5a43.jpg https://i.ibb.co/3ypTH5Mp/38d7bae7a7ab97e00fc9507b6667d38c.jpg https://i.ibb.co/kVqT7yxF/39db70fa1c6a77721245b348bc7859b7.jpg https://i.ibb.co/yFGmCk22/55e3da396b527172e1cef191655be27b.jpg https://i.ibb.co/VYPmZrg2/77a61d9596dd75b46edaa303e6e969e3.jpg https://i.ibb.co/Hfwq4BH5/253dbc5b36f0892a25ea6dbeb9484a59.jpg https://i.ibb.co/gbZ2fvQF/396e16524cf91604021fcff36d34f6f0.jpg https://i.ibb.co/MDHKkrDs/0971e3c586a41a56652d379342ae9370.jpg https://i.ibb.co/WWRcL70n/7468e6368212afc73526c989c937b717.jpg https://i.ibb.co/fWHBwB0/38169b468cb9b0f6fdbd59f6a08184a5.jpg https://i.ibb.co/BVYtrSZZ/73611f128daa13ce74a6740eb1ee0f8d.jpg https://i.ibb.co/gLPDcLPb/2665084084615e6ea6ce121d94068d66.jpg https://i.ibb.co/nN2Hf46H/a317c76e7f6f0856dd4d21888d673f94.jpg https://i.ibb.co/W4KFNNDR/a470c623b44b31dcfbeaa42d796d2233.jpg https://i.ibb.co/Jwd5dC7k/b03d75aa42505c409ebda9839b7d2613.jpg https://i.ibb.co/cKRmJ2bf/b960969cbe2512fc336bc80b4fe0e4d2.jpg https://i.ibb.co/35b6kPXW/be1dd550f5bc74382a48b2d133e2eb28.jpg https://i.ibb.co/Tqh7J1RS/bea75f5e38ce9714f1fb91280a8961b8.jpg https://i.ibb.co/nq7y0dxy/c8b7b290997efc422d43afe2253a0b2d.jpg https://i.ibb.co/ZzvqBmbd/d8becb5e8d7cf7aca25715b1e44b23f7.jpg https://i.ibb.co/rGRgNTg4/f4148f02a79088e7d3cbaa77e5362f8d.jpg https://i.ibb.co/JWf5XV4S/Untitled-design.png https://i.ibb.co/XxbHQ9Gk/9a45465f2734f8605fed7f4af74327d7.jpg https://i.ibb.co/tT3zN48J/11de456850aa9f6658b261e32f251adc.jpg https://i.ibb.co/bjv2mPqm/13c8721971be20487907d888f9499b86.jpg https://i.ibb.co/mrRxhmWZ/015a4efb55c3afcf8ba14f2a3bcfd3fe.jpg https://i.ibb.co/T3N3r9d/26f7a1b317fe45c561e16801a5ca1dac.jpg https://i.ibb.co/h1xBWZ7t/37f6e062f2102ee3f24ef951a31f1187.jpg https://i.ibb.co/VcMwPbv5/286b8c1c0c82369d9dd2de76e376965d.jpg https://i.ibb.co/DfSJcnDy/451eddc019cbfd5771d8eea67cd3a2f1.jpg https://i.ibb.co/C59WqYfx/416846b57cac2dea82ec64e6b5d25143.jpg https://i.ibb.co/ymrgyFYr/651587a924c109a8044c1a644b0eb02d.jpg https://i.ibb.co/35YXNj90/791117c8699dbe3ec06a5b05181140ba.jpg https://i.ibb.co/ZRCNWBYG/4051986ff3e8189ad0b632a5afa4ef55.jpg https://i.ibb.co/VctbyT45/a71cda7519b6bef1a12da8aadc58a226.jpg https://i.ibb.co/Q7Jy0Xt9/a4851b8177e7543e14f50014308bbc6d.jpg https://i.ibb.co/RRQ12vP/b1cfdaaeb073b478b6b55a3082c6e39f.jpg https://i.ibb.co/cKgWD7K5/b8695471815592db698416feb2bea3b8.jpg https://i.ibb.co/4nXjyzNK/bb904bb66452e4cec045da5483a8ded9.jpg https://i.ibb.co/TMRB0Rvr/cacecd9472deaf6950a33bb2abec9658.jpg https://i.ibb.co/sJqXhk69/cb6a673c58e205907a31c86fdd0cf258.jpg https://i.ibb.co/tMtF2bVV/de14c54e3fe99a3f576bd9396517962e.jpg https://i.ibb.co/SDzP8V7t/e414da7e55508a6e6674060b0db53c4f.jpg https://i.ibb.co/4gsQC7WD/e3130de1bd5d7cb390db553b80085c31.jpg https://i.ibb.co/5gQzK63P/ec1780d148293d41ba0785281200decd.jpg https://i.ibb.co/ccWQ3p79/ef8f1b0850464b31162382955ee93c18.jpg https://i.ibb.co/kg0XW9pJ/f1476eccd899f6db25f6696f599a4ca3.jpg')).split()  # Sample pic
NOR_IMG = random.choice(PICS)
MELCOW_VID = environ.get("MELCOW_VID", "https://i.ibb.co/hJn20Bjq/anime-welcome.gif")
SPELL_IMG = environ.get("SPELL_IMG", "CAACAgUAAxkBAAENwWdnqY1AZaRBdPwAAccQMHRwep1PenQAAuQSAAIssohXHigAATpnIXAJNgQ")
SUBSCRIPTION = (environ.get('SUBSCRIPTION', 'https://i.ibb.co/wNcsWpYB/0abea8b13af0f2d75151920ae7ffaf7f.jpg'))
FSUB_PICS = (environ.get('FSUB_PICS', 'https://i.ibb.co/35YXNj90/791117c8699dbe3ec06a5b05181140ba.jpg https://i.ibb.co/ZRCNWBYG/4051986ff3e8189ad0b632a5afa4ef55.jpg https://i.ibb.co/VctbyT45/a71cda7519b6bef1a12da8aadc58a226.jpg https://i.ibb.co/Q7Jy0Xt9/a4851b8177e7543e14f50014308bbc6d.jpg https://i.ibb.co/RRQ12vP/b1cfdaaeb073b478b6b55a3082c6e39f.jpg https://i.ibb.co/cKgWD7K5/b8695471815592db698416feb2bea3b8.jpg https://i.ibb.co/4nXjyzNK/bb904bb66452e4cec045da5483a8ded9.jpg https://i.ibb.co/TMRB0Rvr/cacecd9472deaf6950a33bb2abec9658.jpg https://i.ibb.co/sJqXhk69/cb6a673c58e205907a31c86fdd0cf258.jpg https://i.ibb.co/tMtF2bVV/de14c54e3fe99a3f576bd9396517962e.jpg https://i.ibb.co/SDzP8V7t/e414da7e55508a6e6674060b0db53c4f.jpg https://i.ibb.co/4gsQC7WD/e3130de1bd5d7cb390db553b80085c31.jpg https://i.ibb.co/5gQzK63P/ec1780d148293d41ba0785281200decd.jpg https://i.ibb.co/ccWQ3p79/ef8f1b0850464b31162382955ee93c18.jpg https://i.ibb.co/kg0XW9pJ/f1476eccd899f6db25f6696f599a4ca3.jpg')).split()  # Fsub pic

# ============================
# Admin, Channels & Users Configuration
# ============================
ADMINS = [int(admin) if id_pattern.search(admin) else admin for admin in environ.get('ADMINS', '2090517919').split()] # Replace with the actual admin ID(s) to add
CHANNELS = [int(ch) if id_pattern.search(ch) else ch for ch in environ.get('CHANNELS', '-1002008657265 -1002174163101').split()]  # Channel id for auto indexing (make sure bot is admin)
LOG_CHANNEL = int(environ.get('LOG_CHANNEL', '-1002817571461'))  # Log channel id (make sure bot is admin)
BIN_CHANNEL = int(environ.get('BIN_CHANNEL', '-1002817571461'))  # Bin channel id (make sure bot is admin)
MOVIE_UPDATE_CHANNEL = int(environ.get('MOVIE_UPDATE_CHANNEL', '-1002808090152'))  # Notification of those who verify will be sent to your channel
PREMIUM_LOGS = int(environ.get('PREMIUM_LOGS', '-1002817571461'))  # Premium logs channel id
auth_channel = environ.get('AUTH_CHANNEL', '').strip()  # Single force-sub channel/group ID
DELETE_CHANNELS = [int(dch) if id_pattern.search(dch) else dch for dch in environ.get('DELETE_CHANNELS', '-1002817571461').split()]
support_chat_id = environ.get('SUPPORT_CHAT_ID', '-1002808090152')  # Support group id (make sure bot is admin)
reqst_channel = environ.get('REQST_CHANNEL_ID', '-1002264260689')  # Request channel id (make sure bot is admin)
MULTI_FSUB = [int(channel_id) for channel_id in environ.get('MULTI_FSUB', '-1002808090152 -1001938208245 -1003712608837 -1002226951292').split() if re.match(r'^-?\d+$', channel_id)]  # Channel for force sub (make sure bot is admin)


# ============================
# Payment Configuration
# ============================
QR_CODE = environ.get('QR_CODE', 'https://i.ibb.co/XxbHQ9Gk/9a45465f2734f8605fed7f4af74327d7.jpg')
OWNER_UPI_ID = environ.get('OWNER_UPI_ID', 'Contact @QuirkyContact_Bot for payment')

#Auto approve 
TEXT = environ.get("APPROVED_WELCOME_TEXT", "<b>{mention},\n\nʏᴏᴜʀ ʀᴇǫᴜᴇsᴛ ᴛᴏ ᴊᴏɪɴ {title} ɪs ᴀᴘᴘʀᴏᴠᴇᴅ.\n\‣ ᴘᴏᴡᴇʀᴇᴅ ʙʏ @Quikry</b>")
APPROVED = environ.get("APPROVED_WELCOME", "off").lower()

# Leave this empty to approve requests in every group/channel where the bot is
# an administrator. CHAT_ID is retained as a backwards-compatible alias.
_auto_approve_chat_id = environ.get(
    "AUTO_APPROVE_CHAT_ID", environ.get("CHAT_ID", "")
).strip()
AUTO_APPROVE_CHAT_IDS = [
    int(chat_id) if id_pattern.fullmatch(chat_id) else chat_id
    for chat_id in _auto_approve_chat_id.split()
]


# ============================
# MongoDB Configuration
# ============================
DATABASE_URI = environ.get('DATABASE_URI', "")
DATABASE_URI2 = environ.get('DATABASE_URI2', "")
DATABASE_NAME = environ.get('DATABASE_NAME', "")
COLLECTION_NAME = environ.get('COLLECTION_NAME', 'quirky2')

# ============================
# Movie Notification & Update Settings
# ============================
MOVIE_UPDATE_NOTIFICATION = bool(environ.get('MOVIE_UPDATE_NOTIFICATION', False))  # Notification On (True) / Off (False)
IMAGE_FETCH = bool(environ.get('IMAGE_FETCH', True))  # On (True) / Off (False)
CAPTION_LANGUAGES = ["Bhojpuri", "Hindi", "Bengali", "Tamil", "English", "Bangla", "Telugu", "Malayalam", "Kannada", "Marathi", "Punjabi", "Bengoli", "Gujrati", "Korean", "Gujarati", "Spanish", "French", "German", "Chinese", "Arabic", "Portuguese", "Russian", "Japanese", "Odia", "Assamese", "Urdu"]

# ============================
# Verification Settings
# ============================
VERIFY = bool(environ.get('VERIFY', True))  # Verification On (True) / Off (False)
VERIFY_EXPIRE = int(environ.get('VERIFY_EXPIRE', 6))  # Add time in hours
VERIFIED_LOG = int(environ.get('VERIFIED_LOG', '-1002817571461'))  # Log channel id (make sure bot is admin)
HOW_TO_VERIFY = environ.get('HOW_TO_VERIFY', 'https://t.me/Quikry')  # How to open tutorial link for verification
VERIFY_MINIMUM_SECONDS = int(environ.get('VERIFY_MINIMUM_SECONDS', 50))
SHORTLINK_BYPASS_BAN_HOURS = int(environ.get('SHORTLINK_BYPASS_BAN_HOURS', 6))

# ============================
# Link Shortener Configuration
# ============================
IS_SHORTLINK = bool(environ.get('IS_SHORTLINK', True))
SHORTLINK_URL = environ.get('SHORTLINK_URL', 'inshorturl.com')
SHORTLINK_API = environ.get('SHORTLINK_API', '')
TUTORIAL = environ.get('TUTORIAL', 'https://t.me/Quikry')  # Tutorial video link for opening shortlink website
IS_TUTORIAL = bool(environ.get('IS_TUTORIAL', False))

# ============================
# Channel & Group Links Configuration
# ============================
GRP_LNK = environ.get('GRP_LNK', 'https://t.me/+ejFgz8UdWlcxNWE1')
CHNL_LNK = environ.get('CHNL_LNK', 'https://t.me/Quikry')
OWNER_LNK = environ.get('OWNER_LNK', 'https://t.me/QuirkyContact_Bot')
MOVIE_UPDATE_CHANNEL_LNK = environ.get('MOVIE_UPDATE_CHANNEL_LNK', '')
OWNERID = int(os.environ.get('OWNERID', '2090517919'))  # Replace with the actual admin ID

# ============================
# User Configuration
# ============================
auth_users = [int(user) if id_pattern.search(user) else user for user in environ.get('AUTH_USERS', '2090517919').split()]
AUTH_USERS = (auth_users + ADMINS) if auth_users else []
PREMIUM_USER = [int(user) if id_pattern.search(user) else user for user in environ.get('PREMIUM_USER', '2090517919').split()]

# ============================
# Miscellaneous Configuration
# ============================
NO_RESULTS_MSG = bool(environ.get("NO_RESULTS_MSG", True))  # True if you want no results messages in Log Channel
MAX_B_TN = environ.get("MAX_B_TN", "5")
MAX_BTN = is_enabled((environ.get('MAX_BTN', "True")), True)
PORT = environ.get("PORT", "8080")
MSG_ALRT = environ.get('MSG_ALRT', 'sʜᴀʀᴇ ᴀɴᴅ sᴜᴘᴘᴏʀᴛ ᴜs')
SUPPORT_CHAT = environ.get('SUPPORT_CHAT', 'https://t.me/+ejFgz8UdWlcxNWE1')  # Support group link (make sure bot is admin)
P_TTI_SHOW_OFF = is_enabled((environ.get('P_TTI_SHOW_OFF', "False")), False)
IMDB = is_enabled((environ.get('IMDB', "False")), False)
AUTO_FFILTER = is_enabled((environ.get('AUTO_FFILTER', "True")), True)
AUTO_DELETE = is_enabled((environ.get('AUTO_DELETE', "True")), True)
DELETE_TIME = int(environ.get("DELETE_TIME", "120"))  #  deletion time in seconds (default: 5 minutes). Adjust as per your needs.
SINGLE_BUTTON = is_enabled((environ.get('SINGLE_BUTTON', "True")), False) # pm & Group button or link mode (True) / Off (False)
CUSTOM_FILE_CAPTION = environ.get("CUSTOM_FILE_CAPTION", f"{script.CAPTION}")
BATCH_FILE_CAPTION = environ.get("BATCH_FILE_CAPTION", CUSTOM_FILE_CAPTION)
IMDB_TEMPLATE = environ.get("IMDB_TEMPLATE", f"{script.IMDB_TEMPLATE_TXT}")
LONG_IMDB_DESCRIPTION = is_enabled(environ.get("LONG_IMDB_DESCRIPTION", "False"), False)
SPELL_CHECK_REPLY = is_enabled(environ.get("SPELL_CHECK_REPLY", "True"), True)
MAX_LIST_ELM = environ.get("MAX_LIST_ELM", None)
INDEX_REQ_CHANNEL = int(environ.get('INDEX_REQ_CHANNEL', LOG_CHANNEL))
FILE_STORE_CHANNEL = [int(ch) for ch in (environ.get('FILE_STORE_CHANNEL', '-1002008657265')).split()]
MELCOW_NEW_USERS = is_enabled((environ.get('MELCOW_NEW_USERS', "False")), False)
PROTECT_CONTENT = is_enabled((environ.get('PROTECT_CONTENT', "False")), True)
PUBLIC_FILE_STORE = is_enabled((environ.get('PUBLIC_FILE_STORE', "False")), True)
PM_SEARCH = bool(environ.get('PM_SEARCH', True))  # PM Search On (True) / Off (False)
EMOJI_MODE = bool(environ.get('EMOJI_MODE', True))  # Emoji status On (True) / Off (False)

# ============================
# Bot Configuration
# ============================
auth_grp = environ.get('AUTH_GROUP')
AUTH_CHANNEL = int(auth_channel) if id_pattern.fullmatch(auth_channel) else None
AUTH_GROUPS = [int(ch) for ch in auth_grp.split()] if auth_grp else None
REQST_CHANNEL = int(reqst_channel) if reqst_channel and id_pattern.search(reqst_channel) else None
SUPPORT_CHAT_ID = int(support_chat_id) if support_chat_id and id_pattern.search(support_chat_id) else None
LANGUAGES = ["malayalam", "", "tamil", "", "english", "", "hindi", "", "telugu", "", "kannada", "", "gujarati", "", "marathi", "", "punjabi", ""]
QUALITIES = ["360P", "", "480P", "", "720P", "", "1080P", "", "1440P", "", "2160P", ""]
SEASONS = ["season 1" , "season 2" , "season 3" , "season 4", "season 5" , "season 6" , "season 7" , "season 8" , "season 9" , "season 10"]

# ============================
# Server & Web Configuration
# ============================

STREAM_MODE = bool(environ.get('STREAM_MODE', True)) # Set Stream mode True or False

NO_PORT = bool(environ.get('NO_PORT', False))
APP_NAME = None
if 'DYNO' in environ:
    ON_HEROKU = True
    APP_NAME = environ.get('APP_NAME')
else:
    ON_HEROKU = False
BIND_ADRESS = str(getenv('WEB_SERVER_BIND_ADDRESS', '0.0.0.0'))
FQDN = str(getenv('FQDN', BIND_ADRESS)) if not ON_HEROKU or getenv('FQDN') else APP_NAME+'.herokuapp.com'
URL = "https://{}/".format(FQDN) if ON_HEROKU or NO_PORT else "https://{}/".format(FQDN, PORT)
SLEEP_THRESHOLD = int(environ.get('SLEEP_THRESHOLD', '60'))
WORKERS = int(environ.get('WORKERS', '4'))
SESSION_NAME = str(environ.get('SESSION_NAME', ''))
MULTI_CLIENT = False
name = str(environ.get('name', 'Quirky'))
PING_INTERVAL = int(environ.get("PING_INTERVAL", "1200"))  # 20 minutes
if 'DYNO' in environ:
    ON_HEROKU = True
    APP_NAME = str(getenv('APP_NAME'))
else:
    ON_HEROKU = False
HAS_SSL = bool(getenv('HAS_SSL', True))
if HAS_SSL:
    URL = "https://{}/".format(FQDN)
else:
    URL = "http://{}/".format(FQDN)

# ============================
# Reactions Configuration
# ============================
REACTIONS = ["😇", "🤗", "😍", "👍", "🎅", "😐", "🥰", "🤩", "😱", "🤣", "😘", "👏", "😛", "😈", "🎉", "🫡", "🤓", "😎", "🏆", "🔥", "🤭", "🌚", "🆒", "👻", "😁", "⭐"]



# ============================
# Command admin
# ============================
commands = [
    """• /system - <code>sʏsᴛᴇᴍ ɪɴғᴏʀᴍᴀᴛɪᴏɴ</code>
• /del_msg - <code>ʀᴇᴍᴏᴠᴇ ғɪʟᴇ ɴᴀᴍᴇ ᴄᴏʟʟᴇᴄᴛɪᴏɴ ɴᴏтɪғɪᴄᴀᴛɪᴏн...</code>
• /movie_update - <code>ᴏɴ ᴏғғ ᴀᴄᴄᴏʀᴅɪɴɢ ʏᴏᴜʀ ɴᴇᴇᴅᴇᴅ...</code>
• /pm_search - <code>ᴘᴍ sᴇᴀʀᴄʜ ᴏɴ ᴏғғ ᴀᴄᴄᴏʀᴅɪɴɢ ʏᴏᴜʀ ɴᴇᴇᴅᴇᴅ...</code>
• /logs - <code>ɢᴇᴛ ᴛʜᴇ ʀᴇᴄᴇɴᴛ ᴇʀʀᴏʀꜱ.</code>
• /delete - <code>ᴅᴇʟᴇᴛᴇ ᴀ ꜱᴘᴇᴄɪꜰɪᴄ ꜰɪʟᴇ ꜰʀᴏᴍ ᴅʙ.</code>
• /users - <code>ɢᴇᴛ ʟɪꜱᴛ ᴏꜰ ᴍʏ ᴜꜱᴇʀꜱ ᴀɴᴅ ɪᴅꜱ.</code>
• /chats - <code>ɢᴇᴛ ʟɪꜱᴛ ᴏꜰ ᴍʏ ᴄʜᴀᴛꜱ ᴀɴᴅ ɪᴅꜱ.</code>
• /leave  - <code>ʟᴇᴀᴠᴇ ꜰʀᴏᴍ ᴀ ᴄʜᴀᴛ.</code>
• /disable  -  <code>ᴅɪꜱᴀʙʟᴇ ᴀ ᴄʜᴀᴛ.</code>""",

    """• /ban  - <code>ʙᴀɴ ᴀ ᴜꜱᴇʀ.</code>
• /unban  - <code>ᴜɴʙᴀɴ ᴀ ᴜꜱᴇʀ.</code>
• /channel - <code>ɢᴇᴛ ʟɪꜱᴛ ᴏꜰ ᴛᴏᴛᴀʟ ᴄᴏɴɴᴇᴄᴛᴇᴅ ɢʀᴏᴜᴘꜱ.</code>
• /broadcast - <code>ʙʀᴏᴀᴅᴄᴀꜱᴛ ᴀ ᴍᴇꜱꜱᴀɢᴇ ᴛᴏ ᴀʟʟ ᴜꜱᴇʀꜱ.</code>
• /groupcastcast - <code>Bʀᴏᴀᴅᴄᴀsᴛ ᴀ ᴍᴇssᴀɢᴇ ᴛᴏ ᴀʟʟ ᴄᴏɴɴᴇᴄᴛᴇᴅ ɢʀᴏᴜᴘs</code>
• /clear_junk -  <code> ᴄʟᴇᴀʀ ᴜsᴇʀ ᴊᴜɴᴋ  </code>
• /junk_group -  <code> ᴄʟᴇᴀʀ ɢʀᴏᴜᴘ ᴊᴜɴᴋ  </code>
• /gfilter - <code>ᴀᴅᴅ ɢʟᴏʙᴀʟ ғɪʟᴛᴇʀs.</code>
• /gfilters - <code>ᴠɪᴇᴡ ʟɪsᴛ ᴏғ ᴀʟʟ ɢʟᴏʙᴀʟ ғɪʟᴛᴇʀs.</code>
• /delg - <code>ᴅᴇʟᴇᴛᴇ ᴀ sᴘᴇᴄɪғɪᴄ ɢʟᴏʙᴀʟ ғɪʟᴛᴇʀ.</code>
• /delallg - <code>ᴅᴇʟᴇᴛᴇ ᴀʟʟ Gғɪʟᴛᴇʀs ғʀᴏᴍ ᴛʜᴇ ʙᴏᴛ's ᴅᴀᴛᴀʙᴀsᴇ.</code>
• /deletefiles - <code>ᴅᴇʟᴇᴛᴇ CᴀᴍRɪᴘ ᴀɴᴅ PʀᴇDVD ғɪʟᴇs ғʀᴏᴍ ᴛʜᴇ ʙᴏᴛ's ᴅᴀᴛᴀʙᴀsᴇ.</code>
• /send - <code>ꜱᴇɴᴅ ᴍᴇꜱꜱᴀɢᴇ ᴛᴏ ᴀ ᴘᴀʀᴛɪᴄᴜʟᴀʀ ᴜꜱᴇʀ.</code>""",

    """• /add_premium - <code>ᴀᴅᴅ ᴀɴʏ ᴜꜱᴇʀ ᴛᴏ ᴘʀᴇᴍɪᴜᴍ.</code>
• /remove_premium - <code>ʀᴇᴍᴏᴠᴇ ᴀɴʏ ᴜꜱᴇʀ ꜰʀᴏᴍ ᴘʀᴇᴍɪᴜᴍ.</code>
• /premium_users - <code>ɢᴇᴛ ʟɪꜱᴛ ᴏꜰ ᴘʀᴇᴍɪᴜᴍ ᴜꜱᴇʀꜱ.</code>
• /get_premium - <code>ɢᴇᴛ ɪɴꜰᴏ ᴏꜰ ᴀɴʏ ᴘʀᴇᴍɪᴜᴍ ᴜꜱᴇʀ.</code>
• /restart - <code>ʀᴇꜱᴛᴀʀᴛ ᴛʜᴇ ʙᴏᴛ.</code>"""
]

# ============================
# Command Bot
# ============================
Bot_cmds = {
    "start": "Sᴛᴀʀᴛ Mᴇ Bᴀʙʏ",
    "alive": " Cʜᴇᴄᴋ Bᴏᴛ Aʟɪᴠᴇ ᴏʀ Nᴏᴛ ",
    "settings": "ᴄʜᴀɴɢᴇ sᴇᴛᴛɪɴɢs",
    "id": "ɢᴇᴛ ɪᴅ ᴛᴇʟᴇɢʀᴀᴍ ",
    "info": "Gᴇᴛ Usᴇʀ ɪɴғᴏ ",
    "system": "sʏsᴛᴇᴍ ɪɴғᴏʀᴍᴀᴛɪᴏɴ",
    "del_msg": "ʀᴇᴍᴏᴠᴇ ғɪʟᴇ ɴᴀᴍᴇ ᴄᴏʟʟᴇᴄᴛɪᴏɴ ɴᴏтɪғɪᴄᴀᴛɪᴏɴ...",
    "movie_update": "ᴏɴ ᴏғғ ᴀᴄᴄᴏʀᴅɪɴɢ ʏᴏᴜʀ ɴᴇᴇᴅᴇᴅ...",
    "pm_search": "ᴘᴍ sᴇᴀʀᴄʜ ᴏɴ ᴏғғ ᴀᴄᴄᴏʀᴅɪɴɢ ʏᴏᴜʀ ɴᴇᴇᴅᴇᴅ...",
    "trendlist": "Gᴇᴛ Tᴏᴘ Tʀᴀɴᴅɪɴɢ Sᴇᴀʀᴄʜ Lɪsᴛ",
    "logs": "ɢᴇᴛ ᴛʜᴇ ʀᴇᴄᴇɴᴛ ᴇʀʀᴏʀꜱ.",
    "delete": "ᴅᴇʟᴇᴛᴇ ᴀ ꜱᴘᴇᴄɪꜰɪᴄ ꜰɪʟᴇ ꜰʀᴏᴍ ᴅʙ.",
    "users": "ɢᴇᴛ ʟɪꜱᴛ ᴏꜰ ᴍʏ ᴜꜱᴇʀꜱ ᴀɴᴅ ɪᴅꜱ.",
    "chats": "ɢᴇᴛ ʟɪꜱᴛ ᴏꜰ ᴍʏ ᴄʜᴀᴛꜱ ᴀɴᴅ ɪᴅꜱ.",
    "leave": "ʟᴇᴀᴠᴇ ꜰʀᴏᴍ ᴀ ᴄʜᴀᴛ.",
    "disable": "ᴅɪꜱᴀʙʟᴇ ᴀ ᴄʜᴀᴛ.",
    "ban": "ʙᴀɴ ᴀ ᴜꜱᴇʀ.",
    "unban": "ᴜɴʙᴀɴ ᴀ ᴜꜱᴇʀ.",
    "channel": "ɢᴇᴛ ʟɪꜱᴛ ᴏғ ᴛᴏᴛᴀʟ ᴄᴏɴɴᴇᴄᴛᴇᴅ ɢʀᴏᴜᴘꜱ.",
    "broadcast": "ʙʀᴏᴀᴅᴄᴀꜱᴛ ᴀ ᴍᴇꜱꜱᴀɢᴇ ᴛᴏ ᴀʟʟ ᴜꜱᴇʀꜱ.",
    "groupcast": "ʙʀᴏᴀᴅᴄᴀsᴛ ᴀ ᴍᴇssᴀɢᴇ ᴛᴏ ᴀʟʟ ᴄᴏɴɴᴇᴄᴛᴇᴅ ɢʀᴏᴜᴘs",
    "clear_junk": "ᴄʟᴇᴀʀ ᴜsᴇʀ ᴊᴜɴᴋ",
    "junk_group": "ᴄʟᴇᴀʀ ɢʀᴏᴜᴘ ᴊᴜɴᴋ",
    "gfilter": "ᴀᴅᴅ ɢʟᴏʙᴀʟ ғɪʟᴛᴇʀs.",
    "gfilters": "ᴠɪᴇᴡ ʟɪsᴛ ᴏғ ᴀʟʟ ɢʟᴏʙᴀʟ ғɪʟᴛᴇʀs.",
    "delg": "ᴅᴇʟᴇᴛᴇ ᴀ sᴘᴇᴄɪғɪᴄ ɢʟᴏʙᴀʟ ғɪʟᴛᴇʀ.",
    "delallg": "ᴅᴇʟᴇᴛᴇ ᴀʟʟ Gғɪʟᴛᴇʀs ғʀᴏᴍ ᴛʜᴇ ʙᴏᴛ's ᴅᴀᴛᴀʙᴀsᴇ.",
    "deletefiles": "ᴅᴇʟᴇᴛᴇ CᴀᴍRɪᴘ ᴀɴᴅ PʀᴇDVD ғɪʟᴇs ғʀᴏᴍ ᴛʜᴇ ʙᴏᴛ's ᴅᴀᴛᴀʙᴀsᴇ.",
    "send": "ꜱᴇɴᴅ ᴍᴇꜱꜱᴀɢᴇ ᴛᴏ ᴀ ᴘᴀʀᴛɪᴄᴜʟᴀʀ ᴜꜱᴇʀ.",
    "add_premium": "ᴀᴅᴅ ᴀɴʏ ᴜꜱᴇʀ ᴛᴏ ᴘʀᴇᴍɪᴜᴍ.",
    "remove_premium": "ʀᴇᴍᴏᴠᴇ ᴀɴʏ ᴜꜱᴇʀ ꜰʀᴏᴍ ᴘʀᴇᴍɪᴜᴍ.",
    "premium_users": "ɢᴇᴛ ʟɪꜱᴛ ᴏꜰ ᴘʀᴇᴍɪᴜᴍ ᴜꜱᴇʀꜱ.",
    "get_premium": "ɢᴇᴛ ɪɴꜰᴏ ᴏꜰ ᴀɴʏ ᴘʀᴇᴍɪᴜᴍ ᴜꜱᴇʀ.",
    "restart": "ʀᴇꜱᴛᴀʀᴛ ᴛʜᴇ ʙᴏᴛ."
}




# ============================
# Logs Configuration
# ============================
LOG_STR = "Current Customized Configurations are:-\n"
LOG_STR += ("IMDB Results are enabled, Bot will be showing imdb details for your queries.\n" if IMDB else "IMDB Results are disabled.\n")
LOG_STR += ("P_TTI_SHOW_OFF found, Users will be redirected to send /start to Bot PM instead of sending file directly.\n" if P_TTI_SHOW_OFF else "P_TTI_SHOW_OFF is disabled, files will be sent in PM instead of starting the bot.\n")
LOG_STR += ("SINGLE_BUTTON is found, filename and file size will be shown in a single button instead of two separate buttons.\n" if SINGLE_BUTTON else "SINGLE_BUTTON is disabled, filename and file size will be shown as different buttons.\n")
LOG_STR += (f"CUSTOM_FILE_CAPTION enabled with value {CUSTOM_FILE_CAPTION}, your files will be sent along with this customized caption.\n" if CUSTOM_FILE_CAPTION else "No CUSTOM_FILE_CAPTION Found, Default captions of file will be used.\n")
LOG_STR += ("Long IMDB storyline enabled." if LONG_IMDB_DESCRIPTION else "LONG_IMDB_DESCRIPTION is disabled, Plot will be shorter.\n")
LOG_STR += ("Spell Check Mode is enabled, bot will be suggesting related movies if movie name is misspelled.\n" if SPELL_CHECK_REPLY else "Spell Check Mode is disabled.\n")

