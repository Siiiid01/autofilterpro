from aiohttp import web
import re
import math
import logging
import secrets
import time
import mimetypes
from pathlib import Path
import jinja2
from urllib.parse import urlencode
from aiohttp.http_exceptions import BadStatusLine
from LucyBot.Bot import multi_clients, work_loads, Codeflix
from LucyBot.server.exceptions import FIleNotFound, InvalidHash
from LucyBot.zzint import StartTime, __version__
from LucyBot.util.custom_dl import ByteStreamer
from LucyBot.util.time_format import get_readable_time
from LucyBot.util.render_template import render_page
from info import *
from utils import temp, get_verify_shorted_link
from database.users_chats_db import db as userdb


routes = web.RouteTableDef()

SHORTLINK_TEMPLATE = Path(__file__).resolve().parent.parent / "LucyBot" / "template" / "shortlink.htm"

def render_shortlink_page(**context):
    with SHORTLINK_TEMPLATE.open(encoding="utf-8") as template_file:
        return jinja2.Template(template_file.read()).render(**context)

@routes.get("/", allow_head=True)
async def root_route_handler(request):
    return web.json_response("Lucy_Bot")


@routes.get(r"/v/{token:[A-Za-z0-9]+}", allow_head=True)
async def verify_redirect_handler(request: web.Request):
    """Resolve an opaque FQDN verification URL into a Telegram deep link."""
    token = request.match_info['token']
    verify_link = temp.VERIFY_LINKS.get(token)
    # DB fallback: token may have been issued before last restart
    if not verify_link:
        try:
            verify_link = await userdb.get_verify_token(token)
            if verify_link:
                temp.VERIFY_LINKS[token] = verify_link  # re-populate cache
        except Exception:
            pass
    if not verify_link:
        raise web.HTTPNotFound(text="This verification link is invalid or has expired. Please request a new one from the bot.")
    start_payload = f"verify-{verify_link['user_id']}-{token}"
    raise web.HTTPFound(f"https://t.me/{temp.U_NAME}?{urlencode({'start': start_payload})}")


@routes.get(r"/go/{token:[A-Za-z0-9]+}", allow_head=True)
async def verify_landing_handler(request: web.Request):
    """Serve a premium landing page. The user sees only the FQDN /v/ URL — never the shortlink."""
    token = request.match_info['token']
    verify_link = temp.VERIFY_LINKS.get(token)
    # DB fallback: re-populate cache if bot restarted
    if not verify_link:
        try:
            verify_link = await userdb.get_verify_token(token)
            if verify_link:
                temp.VERIFY_LINKS[token] = verify_link
        except Exception:
            pass
    if not verify_link:
        raise web.HTTPNotFound(text="This verification link is invalid or has expired. Please request a new one from the bot.")

    # The /v/ FQDN URL is what the shortlink will redirect to after the ad page.
    # The user never sees the shortlink URL directly — only the FQDN in the button.
    verify_fqdn_url = f"{URL.rstrip('/')}/v/{token}"
    # Shorten the internal /v/ URL for the actual verification flow (ad page)
    try:
        shortened_url = await get_verify_shorted_link(verify_fqdn_url)
    except Exception:
        shortened_url = verify_fqdn_url  # fallback: use FQDN directly

    html = render_shortlink_page(
        title="Verify to Get File",
        eyebrow="Secure access",
        mark="↗",
        heading="Verify to continue.",
        description="Complete the short verification step to unlock your requested file.",
        status="Preparing secure link",
        waiting_label="Preparing link",
        waiting_note="The button becomes available when the countdown ends.",
        ready_label="Continue to verification",
        ready_note="Your secure link is ready.",
        target=shortened_url,
    )
    return web.Response(text=html, content_type="text/html")


@routes.get(r"/sl/{token:[A-Za-z0-9_-]+}", allow_head=True)
async def shortlink_redirect_handler(request: web.Request):
    import base64
    token = request.match_info['token']
    try:
        padding = '=' * (-len(token) % 4)
        shortlink = base64.urlsafe_b64decode(token + padding).decode('utf-8')
        
        html = render_shortlink_page(
            title="Download Your File",
            eyebrow="Secure download",
            mark="↓",
            heading="Your file is ready.",
            description="Your secure download link is being prepared. Stay on this page until the timer completes.",
            status="Preparing download",
            waiting_label="Preparing link",
            waiting_note="The download button will unlock when the countdown ends.",
            ready_label="Start download",
            ready_note="Your secure download is ready.",
            target=shortlink,
        )
        return web.Response(text=html, content_type="text/html")
    except Exception as e:
        if isinstance(e, web.HTTPFound):
            raise e
        raise web.HTTPNotFound(text="Invalid shortlink token")


@routes.get(r"/watch/{path:\S+}", allow_head=True)
async def stream_handler(request: web.Request):
    try:
        path = request.match_info["path"]
        match = re.search(r"^([a-zA-Z0-9_-]{6})(\d+)$", path)
        if match:
            secure_hash = match.group(1)
            id = int(match.group(2))
        else:
            id = int(re.search(r"(\d+)(?:\/\S+)?", path).group(1))
            secure_hash = request.rel_url.query.get("hash")
        return web.Response(text=await render_page(id, secure_hash), content_type='text/html')
    except InvalidHash as e:
        raise web.HTTPForbidden(text=e.message)
    except FIleNotFound as e:
        raise web.HTTPNotFound(text=e.message)
    except (AttributeError, BadStatusLine, ConnectionResetError):
        pass
    except Exception as e:
        logging.critical(e.with_traceback(None))
        raise web.HTTPInternalServerError(text=str(e))

@routes.get(r"/{path:\S+}", allow_head=True)
async def catch_all_stream_handler(request: web.Request):
    try:
        path = request.match_info["path"]
        match = re.search(r"^([a-zA-Z0-9_-]{6})(\d+)$", path)
        if match:
            secure_hash = match.group(1)
            id = int(match.group(2))
        else:
            id = int(re.search(r"(\d+)(?:\/\S+)?", path).group(1))
            secure_hash = request.rel_url.query.get("hash")
        return await media_streamer(request, id, secure_hash)
    except InvalidHash as e:
        raise web.HTTPForbidden(text=e.message)
    except FIleNotFound as e:
        raise web.HTTPNotFound(text=e.message)
    except (AttributeError, BadStatusLine, ConnectionResetError):
        pass
    except Exception as e:
        logging.critical(e.with_traceback(None))
        raise web.HTTPInternalServerError(text=str(e))

class_cache = {}

async def media_streamer(request: web.Request, id: int, secure_hash: str):
    range_header = request.headers.get("Range", 0)
    
    index = min(work_loads, key=work_loads.get)
    faster_client = multi_clients[index]
    
    if MULTI_CLIENT:
        logging.info(f"Client {index} is now serving {request.remote}")

    if faster_client in class_cache:
        tg_connect = class_cache[faster_client]
        logging.debug(f"Using cached ByteStreamer object for client {index}")
    else:
        logging.debug(f"Creating new ByteStreamer object for client {index}")
        tg_connect = ByteStreamer(faster_client)
        class_cache[faster_client] = tg_connect
    logging.debug("before calling get_file_properties")
    file_id = await tg_connect.get_file_properties(id)
    logging.debug("after calling get_file_properties")
    
    if file_id.unique_id[:6] != secure_hash:
        logging.debug(f"Invalid hash for message with ID {id}")
        raise InvalidHash
    
    file_size = file_id.file_size

    if range_header:
        from_bytes, until_bytes = range_header.replace("bytes=", "").split("-")
        from_bytes = int(from_bytes)
        until_bytes = int(until_bytes) if until_bytes else file_size - 1
    else:
        from_bytes = request.http_range.start or 0
        until_bytes = (request.http_range.stop or file_size) - 1

    if (until_bytes > file_size) or (from_bytes < 0) or (until_bytes < from_bytes):
        return web.Response(
            status=416,
            body="416: Range not satisfiable",
            headers={"Content-Range": f"bytes */{file_size}"},
        )

    chunk_size = 1024 * 1024
    until_bytes = min(until_bytes, file_size - 1)

    offset = from_bytes - (from_bytes % chunk_size)
    first_part_cut = from_bytes - offset
    last_part_cut = until_bytes % chunk_size + 1

    req_length = until_bytes - from_bytes + 1
    part_count = math.ceil(until_bytes / chunk_size) - math.floor(offset / chunk_size)
    body = tg_connect.yield_file(
        file_id, index, offset, first_part_cut, last_part_cut, part_count, chunk_size
    )

    mime_type = file_id.mime_type
    file_name = file_id.file_name
    disposition = "attachment"

    if mime_type:
        if not file_name:
            try:
                file_name = f"{secrets.token_hex(2)}.{mime_type.split('/')[1]}"
            except (IndexError, AttributeError):
                file_name = f"{secrets.token_hex(2)}.unknown"
    else:
        if file_name:
            mime_type = mimetypes.guess_type(file_id.file_name)
        else:
            mime_type = "application/octet-stream"
            file_name = f"{secrets.token_hex(2)}.unknown"

    return web.Response(
        status=206 if range_header else 200,
        body=body,
        headers={
            "Content-Type": f"{mime_type}",
            "Content-Range": f"bytes {from_bytes}-{until_bytes}/{file_size}",
            "Content-Length": str(req_length),
            "Content-Disposition": f'{disposition}; filename="{file_name}"',
            "Accept-Ranges": "bytes",
        },
    )
