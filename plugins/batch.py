import os
import re
import time
import asyncio
import json
import logging
import random
import shutil
import aiofiles
from motor.motor_asyncio import AsyncIOMotorClient
from pyrogram import Client, filters
from pyrogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from pyrogram.errors import UserNotParticipant, FloodWait

# Local Imports
from config import API_ID, API_HASH, STRING, FORCE_SUB, FREEMIUM_LIMIT, PREMIUM_LIMIT, MONGO_DB, DB_NAME
from utils.func import db, get_user_data, screenshot, thumbnail, get_video_metadata, save_user_data
from utils.func import get_user_data_key, process_text_with_rules, is_premium_user, E, log_admin_activity, get_display_name
from utils.func import generate_thumbnail, beautify_caption, download_youtube_video, copy_header_and_repair
from shared_client import app as X
from plugins.start import subscribe as sub
from utils.custom_filters import login_in_progress
from utils.encrypt import dcs
from typing import Dict, Any, Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logging.getLogger("pyrogram.session.session").setLevel(logging.ERROR)

Y = None if not STRING else __import__('shared_client').userbot
Z, P, UB, UC = {}, {}, {}, {}
FIX_DATA = {}

ACTIVE_USERS = {}
ACTIVE_USERS_FILE = "active_users.json"
LAST_UPDATE_TIME = {}
PROGRESS_LINKS = {} 

cancel_kb = ReplyKeyboardMarkup([[KeyboardButton("❌ Cancel")]], resize_keyboard=True, one_time_keyboard=True)

try:
    cache_col = db["file_cache"]
    topic_cache_col = db["topic_cache"]  
    logger.info("✅ MongoDB File & Topic Cache connected from global pool!")
except Exception as e:
    cache_col = None
    topic_cache_col = None
    logger.warning("⚠️ MongoDB caching disabled.")

def load_active_users():
    try:
        if os.path.exists(ACTIVE_USERS_FILE):
            with open(ACTIVE_USERS_FILE, 'r') as f:
                return json.load(f)
        return {}
    except Exception:
        return {}

async def save_active_users_to_file():
    try:
        async with aiofiles.open(ACTIVE_USERS_FILE, 'w') as f:
            await f.write(json.dumps(ACTIVE_USERS))
    except Exception as e:
        logger.error(f"⚠️ Failed to save active users file: {e}")

async def add_active_batch(user_id: int, batch_info: Dict[str, Any]):
    ACTIVE_USERS[str(user_id)] = batch_info
    await save_active_users_to_file()

def is_user_active(user_id: int) -> bool:
    return str(user_id) in ACTIVE_USERS

async def update_batch_progress(user_id: int, current: int, success: int):
    if str(user_id) in ACTIVE_USERS:
        ACTIVE_USERS[str(user_id)]["current"] = current
        ACTIVE_USERS[str(user_id)]["success"] = success

async def request_batch_cancel(user_id: int):
    if str(user_id) in ACTIVE_USERS:
        ACTIVE_USERS[str(user_id)]["cancel_requested"] = True
        await save_active_users_to_file()
        return True
    return False

def should_cancel(user_id: int) -> bool:
    user_str = str(user_id)
    return user_str in ACTIVE_USERS and ACTIVE_USERS[user_str].get("cancel_requested", False)

async def remove_active_batch(user_id: int):
    if str(user_id) in ACTIVE_USERS:
        del ACTIVE_USERS[str(user_id)]
        await save_active_users_to_file()

ACTIVE_USERS = load_active_users()

async def get_msg(c, u, i, d, lt):
    try:
        if lt == 'public':
            try:
                msg = await c.get_messages(i, d)
                if msg and not getattr(msg, "empty", False): return msg
            except FloodWait as fw:
                await asyncio.sleep(fw.value + 5)
                msg = await c.get_messages(i, d)
                if msg and not getattr(msg, "empty", False): return msg
            except Exception: pass
            
            if u:
                try:
                    msg = await u.get_messages(i, d)
                    if msg and not getattr(msg, "empty", False): return msg
                except FloodWait as fw:
                    await asyncio.sleep(fw.value + 5)
                    msg = await u.get_messages(i, d)
                    if msg and not getattr(msg, "empty", False): return msg
                except Exception: pass
            return None
        else:
            if u:
                try:
                    i_str = str(i)
                    targets = []
                    if i_str.lstrip('-').isdigit():
                        base_id = i_str.lstrip('-')
                        targets = [int(f"-100{base_id}"), int(f"-{base_id}"), int(i_str)]
                    else:
                        targets = [i]
                    
                    for target_id in targets:
                        try:
                            result = await u.get_messages(target_id, d)
                            if result and not getattr(result, "empty", False): return result
                        except FloodWait as fw:
                            await asyncio.sleep(fw.value + 5)
                            result = await u.get_messages(target_id, d)
                            if result and not getattr(result, "empty", False): return result
                        except Exception: pass
                    return None
                except Exception: return None
            return None
    except Exception: return None

async def get_ubot(uid):
    bt = await get_user_data_key(uid, "bot_token", None)
    if not bt: return None
    
    # 1. Connected state check karo
    if uid in UB: 
        bot = UB.get(uid)
        if bot and not bot.is_connected:
            try: await bot.start()
            except: pass
        return bot
        
    try:
        # 🔥 FIX: Added in_memory=True to prevent SQLite DB Corruption & Lock issues
        bot = Client(f"user_{uid}", bot_token=bt, api_id=API_ID, api_hash=API_HASH, in_memory=True)
        await bot.start()
        UB[uid] = bot
        return bot
    except Exception as e:
        logger.error(f"Error starting UBOT for {uid}: {e}") # Isse terminal me asli error dikhega
        return None

async def get_uclient(uid):
    ud = await get_user_data(uid)
    ubot = UB.get(uid)
    cl = UC.get(uid)
    
    if cl:
        if not cl.is_connected:
            try: await cl.connect()
            except: pass
        return cl
        
    if not ud: return ubot if ubot else None
    
    xxx = ud.get('session_string')
    if xxx:
        try:
            ss = dcs(xxx)
            from utils.func import get_or_create_fingerprint
            fingerprint = await get_or_create_fingerprint(uid)
            
            gg = Client(
                f'{uid}_client', 
                api_id=API_ID, 
                api_hash=API_HASH, 
                session_string=ss,
                in_memory=True, # 🔥 FIX: Ram Session to avoid SQLite Lock on user sessions
                device_model=fingerprint.get("device_model", "Realme P3 Pro"),
                system_version=fingerprint.get("system_version", "Android 14"),
                app_version=fingerprint.get("app_version", "10.14.0"),
                lang_code=fingerprint.get("lang_code", "en"),
                max_concurrent_transmissions=1,
                sleep_threshold=120
            )
            await gg.start()
            UC[uid] = gg
            return gg
        except Exception as e:
            logger.error(f"Error starting UCLIENT for {uid}: {e}")
            return ubot if ubot else Y
            
    return Y

async def prog(c, t, C, h, m, st, action="Downloading......."):
    global LAST_UPDATE_TIME
    p = c / t * 100
    now = time.time()
    
    if m not in LAST_UPDATE_TIME or (now - LAST_UPDATE_TIME.get(m, 0)) >= 11 or p >= 100:
        LAST_UPDATE_TIME[m] = now
        c_mb = c / (1024 * 1024)
        t_mb = t / (1024 * 1024)
        
        completed_blocks = int(p / 10)
        remaining_blocks = 10 - completed_blocks
        bar = '🟢' * completed_blocks + '🔴' * remaining_blocks
        
        speed = c / (now - st) / (1024 * 1024) if now > st else 0
        eta = time.strftime('%M:%S', time.gmtime((t - c) / (speed * 1024 * 1024))) if speed > 0 else '00:00'
        
        info = PROGRESS_LINKS.get(m, {})
        src_name = info.get("name", "Unknown")
        idx = info.get("index", "Unknown")
        link = info.get("link", "")
        
        src_str = f"📢 **Channel:** `{src_name}`\n🔢 **Index:** `{idx}`\n" if src_name != "Unknown" else ""
        link_str = f"🔗 **Link:** {link}\n" if link else ""
        
        text = f"__**H4R SRC Progress**__\n{src_str}{link_str}🔄 **Action:** {action}\n\n{bar}\n\n⚡ **Completed:** {c_mb:.2f} MB / {t_mb:.2f} MB\n📊 **Done:** {p:.2f}%\n🚀 **Speed:** {speed:.2f} MB/s\n⏳ **ETA:** {eta}\n\n**__Powered by H4R__**"
        
        async def safe_edit():
            try: 
                await C.edit_message_text(h, m, text, disable_web_page_preview=True)
            except FloodWait as fw:
                LAST_UPDATE_TIME[m] = time.time() + fw.value
            except Exception: 
                pass
            
        asyncio.create_task(safe_edit())
        if p >= 100: 
            LAST_UPDATE_TIME.pop(m, None)
            if p >= 100 and action == "Uploading.....":
                PROGRESS_LINKS.pop(m, None)

async def safe_status_edit(client, chat_id, msg_id, text):
    info = PROGRESS_LINKS.get(msg_id, {})
    src_name = info.get("name", "Unknown")
    idx = info.get("index", "Unknown")
    link = info.get("link", "")
    
    src_str = f"\n\n📢 **Channel:** `{src_name}`\n🔢 **Index:** `{idx}`" if src_name != "Unknown" else ""
    link_str = f"\n🔗 **Link:** {link}" if link else ""
    
    full_text = f"{text}{src_str}{link_str}"
    try: 
        await client.edit_message_text(chat_id, msg_id, full_text, disable_web_page_preview=True)
    except Exception: 
        pass

async def process_msg(c, u, m, d, lt, uid, i, task=None, dest_thread_id=None):
    if isinstance(d, str):
        try: d = int(d)
        except Exception: pass

    tcid = d
    rtmid = dest_thread_id if dest_thread_id else None
    p = None 

    try:
        if task and task.get("doc_only", False):
            if getattr(m, 'video', None) or getattr(m, 'animation', None) or getattr(m, 'video_note', None):
                return 'Done (Skipped Video)'

        orig_text = m.caption.markdown if m.caption else (m.text.markdown if m.text else '')

        if m.media:
            proc_text = await process_text_with_rules(uid, orig_text)
            user_cap = await get_user_data_key(uid, 'caption', '')
            raw_caption = f'{proc_text}\n\n{user_cap}' if proc_text and user_cap else user_cap if user_cap else proc_text
            
            if task:
                for old, new in task.get("replace_dict", {}).items(): 
                    raw_caption = re.sub(re.escape(old), new, raw_caption, flags=re.IGNORECASE)
                for word in task.get("remove_list", []): 
                    raw_caption = re.sub(re.escape(word), "", raw_caption, flags=re.IGNORECASE)
            
            raw_caption = re.sub(r'\.(mp4|mkv|pdf|avi|webm|jpg|png)', '', raw_caption, flags=re.IGNORECASE)
            raw_caption = re.sub(r'(?i)Number Of Digits', 'No. of Digit', raw_caption)
            
            from utils.func import ai_rewrite_caption
            
            extractor_name = await get_user_data_key(uid, "extractor_name", "🇮‌🇹‌'🇸‌ 🇭‌4⃣🇷‌")
            if not extractor_name or extractor_name.strip() == "":
                extractor_name = "🇮‌🇹‌'🇸‌ 🇭‌4⃣🇷‌"
                
            file_name_context = ""
            if m.document: file_name_context = getattr(m.document, 'file_name', '')
            elif m.video: file_name_context = getattr(m.video, 'file_name', '')
            elif m.audio: file_name_context = getattr(m.audio, 'file_name', '')
            
            custom_template = task.get("manual_caption") if task else None
            skip_ai = task.get("skip_ai", False) if task else False
            
            if skip_ai:
                ft = raw_caption
            else:
                try:
                    ft = await ai_rewrite_caption(
                        original_caption=raw_caption, 
                        file_name=file_name_context, 
                        custom_name=extractor_name,
                        custom_template=custom_template
                    )
                    if file_name_context and "{filename}" in ft:
                        ft = ft.replace("{filename}", file_name_context)
                except Exception as e:
                    logger.error(f"AI Rewriter Error: {e}")
                    if custom_template:
                        ft = custom_template.replace("{filename}", file_name_context)
                    else:
                        ft = raw_caption
                
            is_restricted = getattr(m.chat, "has_protected_content", False) if m.chat else False
            direct_forward = await get_user_data_key(uid, "direct_forward", False)
            
            # ZERO-API OVERHEAD FOR DIRECT FORWARD
            if direct_forward and not is_restricted:
                try:
                    client_to_use = u if (lt == 'private' and u) else c
                    await client_to_use.copy_message(
                        chat_id=tcid, 
                        from_chat_id=i,  
                        message_id=m.id, 
                        caption=ft if ft else None, 
                        reply_to_message_id=rtmid, 
                        message_thread_id=dest_thread_id
                    )
                    return 'Fast Forwarded ✅'
                except FloodWait as fw:
                    await asyncio.sleep(fw.value + 5)
                except Exception as e:
                    logger.warning(f"Direct Forward Failed for Media {i}:{m.id} -> {e}")
                    pass
            
            # ================= DOWNLOAD BLOCK =================
            if lt == 'private':
                msg_link = f"https://t.me/c/{str(i).replace('-100', '')}/{m.id}"
            else:
                msg_link = f"https://t.me/{str(i).replace('-100', '')}/{m.id}"
            
            source_name = task.get("source", str(i)) if task else str(i)
            mid = task.get("current_mid", m.id) if task else m.id
            
            p = await c.send_message(uid, f'⚙️ Initializing...\n\n📢 **Channel:** `{source_name}`\n🔢 **Index:** `{mid}`\n🔗 **Link:** {msg_link}', disable_web_page_preview=True)
            
            PROGRESS_LINKS[p.id] = {
                "link": msg_link,
                "name": source_name,
                "index": mid
            }
            
            st = time.time()
            await safe_status_edit(c, uid, p.id, '⬇️ Downloading...')

            original_ext = ""
            raw_fname = ""
            
            if m.video: 
                original_ext = ".mp4"
                raw_fname = getattr(m.video, 'file_name', '')
            elif m.audio: 
                original_ext = ".mp3"
                raw_fname = getattr(m.audio, 'file_name', '')
            elif m.document: 
                original_ext = os.path.splitext(m.document.file_name)[1].lower() if getattr(m.document, 'file_name', None) else ".pdf"
                raw_fname = getattr(m.document, 'file_name', '')
            elif m.photo: 
                original_ext = ".jpg"
                raw_fname = f"{time.time()}.jpg"
                
            if not raw_fname:
                raw_fname = f"{time.time()}{original_ext}"
                
            final_fname = raw_fname
            if task:
                for old, new in task.get("replace_dict", {}).items():
                    final_fname = re.sub(re.escape(old), new, final_fname, flags=re.IGNORECASE)
                for word in task.get("remove_list", []):
                    final_fname = re.sub(re.escape(word), "", final_fname, flags=re.IGNORECASE)
            
            final_fname = re.sub(r'\s+', ' ', final_fname).strip()
            
            if original_ext and not final_fname.lower().endswith(original_ext):
                final_fname += original_ext
                
            c_name = final_fname
    
            try:
                client_to_use = getattr(m, '_client', u if u else c)
                f = await client_to_use.download_media(m, file_name=c_name, progress=prog, progress_args=(c, uid, p.id, st, "Downloading......."))
            except FloodWait as fw:
                await safe_status_edit(c, uid, p.id, f"⚠️ FloodWait: Sleeping for {fw.value} seconds.")
                await asyncio.sleep(fw.value + 5)
                f = None
            except Exception as e:
                logger.error(f"Media download failed: {e}")
                f = None
                
            if not f:
                await safe_status_edit(c, uid, p.id, 'Failed.')
                return 'Failed.'

            if isinstance(f, str) and f.lower().endswith('.pdf'):
                await safe_status_edit(c, uid, p.id, '📄 Processing PDF Watermarks...')
                
                wm_text = task.get("watermark", "") if task else ""
                remove_list = task.get("remove_list", []) if task else []
                
                from utils.pdf_watermark import process_pdf_watermark
                pdf_processed = f"processed_{os.path.basename(f)}"
                
                success = await asyncio.to_thread(
                    process_pdf_watermark, f, pdf_processed, wm_text, remove_list
                )
                
                if success and os.path.exists(pdf_processed):
                    try:
                        os.remove(f) 
                        f = pdf_processed 
                    except Exception as e:
                        logger.error(f"Failed to swap PDF files: {e}")
            
            await safe_status_edit(c, uid, p.id, '🤖 Applying Final File Name...')
            
            user_rename_tag = await get_user_data_key(uid, 'rename_tag', '')
            if user_rename_tag and os.path.exists(f):
                ext = original_ext if original_ext else os.path.splitext(f)[1]
                base_name = os.path.splitext(os.path.basename(f))[0]
                
                if user_rename_tag not in base_name:
                    new_f_name = f"{base_name} {user_rename_tag}{ext}".strip()
                    new_f_name = re.sub(r'\s+', ' ', new_f_name)
                    
                    dir_name = os.path.dirname(f)
                    new_f_path = os.path.join(dir_name, new_f_name) if dir_name else new_f_name
                    
                    try:
                        os.rename(f, new_f_path)
                        f = new_f_path
                    except Exception as e:
                        logger.error(f"Rename Error: {e}")
                        
            if m.video or (isinstance(f, str) and f.lower().endswith(('.mp4', '.mkv', '.webm'))):
                reference_video_path = f"temp_reference_{uid}.mp4"
                await safe_status_edit(c, uid, p.id, '🔍 Checking video health...')
                
                check_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", f]
                proc = await asyncio.create_subprocess_exec(*check_cmd, stdout=asyncio.subprocess.PIPE)
                stdout, _ = await proc.communicate()
                is_corrupt = not bool(stdout.decode().strip())
                
                if is_corrupt:
                    if os.path.exists(reference_video_path):
                        await safe_status_edit(c, uid, p.id, '🛠 Video Crashed! Copying header from previous good video...')
                        f = await copy_header_and_repair(f, reference_video_path)
                        if not f:
                            await c.delete_messages(uid, p.id)
                            return 'Failed (Unfixable Crash)'
                    else:
                        await safe_status_edit(c, uid, p.id, '❌ Skipped: Video is crashed, but no reference video exists yet.')
                        if os.path.exists(f): 
                            try: os.remove(f)
                            except: pass
                        await c.delete_messages(uid, p.id)
                        return 'Failed (No Reference)'
                else:
                    if not os.path.exists(reference_video_path):
                        shutil.copy2(f, reference_video_path)
                        logger.info("✅ Reference video saved for future header copying.")

            fsize = os.path.getsize(f) / (1024 * 1024 * 1024)
            th = None
            batch_wm = task.get("watermark", "") if task else ""
            
            if m.video or str(f).endswith(('.mp4', '.mkv')):
                 th = await generate_thumbnail(f, batch_wm, uid)
            
            if not th:
                 th = thumbnail(uid)
            
            premium_client = u if u else Y
            if fsize > 2 and premium_client:
                st = time.time()
                await safe_status_edit(c, uid, p.id, 'File is larger than 2GB. Using premium client...')
                mtd = await get_video_metadata(f)
                dur, h, w = mtd['duration'], mtd['width'], mtd['height']
                
                send_funcs = {'video': premium_client.send_video, 'video_note': premium_client.send_video_note, 'voice': premium_client.send_voice, 'audio': premium_client.send_audio, 'photo': premium_client.send_photo, 'document': premium_client.send_document}
                
                try:
                    for mtype, func in send_funcs.items():
                        if f.endswith('.mp4'): 
                            mtype = 'video'
                        if getattr(m, mtype, None):
                            sent = await func(tcid, f, thumb=th if mtype == 'video' else None, duration=dur if mtype == 'video' else None, height=h if mtype == 'video' else None, width=w if mtype == 'video' else None, caption=ft if m.caption and mtype not in ['video_note', 'voice'] else None, reply_to_message_id=rtmid, message_thread_id=dest_thread_id, progress=prog, progress_args=(c, uid, p.id, st, "Uploading....."))
                            break
                    else:
                        sent = await premium_client.send_document(tcid, f, thumb=th, caption=ft if m.caption else None, reply_to_message_id=rtmid, message_thread_id=dest_thread_id, progress=prog, progress_args=(c, uid, p.id, st, "Uploading....."))
                except FloodWait as fw:
                    await safe_status_edit(c, uid, p.id, f"⚠️ FloodWait (2GB+): Sleeping for {fw.value}s...")
                    await asyncio.sleep(fw.value + 5)
                    if f and os.path.exists(f): 
                        try: os.remove(f)
                        except: pass
                    return 'Failed (FloodWait).'
                
                if f and os.path.exists(f):
                    try: os.remove(f)
                    except: pass
                await c.delete_messages(uid, p.id)
                return 'Done (Large file).'
            
            await safe_status_edit(c, uid, p.id, 'Uploading...')
            st = time.time()
            try:
                if m.video or f.lower().endswith(('.mp4', '.mkv', '.webm')):
                    mtd = await get_video_metadata(f)
                    await c.send_video(tcid, video=f, caption=ft if m.caption else None, thumb=th, width=mtd['width'], height=mtd['height'], duration=mtd['duration'], progress=prog, progress_args=(c, uid, p.id, st, "Uploading....."), reply_to_message_id=rtmid, message_thread_id=dest_thread_id)
                elif m.photo or f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                    await c.send_photo(tcid, photo=f, caption=ft if m.caption else None, progress=prog, progress_args=(c, uid, p.id, st, "Uploading....."), reply_to_message_id=rtmid, message_thread_id=dest_thread_id)
                elif m.audio or f.lower().endswith(('.mp3', '.m4a', '.wav')):
                    await c.send_audio(tcid, audio=f, caption=ft if m.caption else None, thumb=th, progress=prog, progress_args=(c, uid, p.id, st, "Uploading....."), reply_to_message_id=rtmid, message_thread_id=dest_thread_id)
                elif m.voice or f.lower().endswith('.ogg'):
                    await c.send_voice(tcid, voice=f, caption=ft if m.caption else None, progress=prog, progress_args=(c, uid, p.id, st, "Uploading....."), reply_to_message_id=rtmid, message_thread_id=dest_thread_id)
                elif m.video_note:
                    await c.send_video_note(tcid, video_note=f, progress=prog, progress_args=(c, uid, p.id, st, "Uploading....."), reply_to_message_id=rtmid, message_thread_id=dest_thread_id)
                elif m.sticker:
                    await c.send_sticker(tcid, sticker=f, progress=prog, progress_args=(c, uid, p.id, st, "Uploading....."), reply_to_message_id=rtmid, message_thread_id=dest_thread_id)
                elif m.animation or f.lower().endswith('.gif'):
                    await c.send_animation(tcid, animation=f, caption=ft if m.caption else None, progress=prog, progress_args=(c, uid, p.id, st, "Uploading....."), reply_to_message_id=rtmid, message_thread_id=dest_thread_id)
                else:
                    await c.send_document(tcid, document=f, caption=ft if m.caption else None, thumb=th, progress=prog, progress_args=(c, uid, p.id, st, "Uploading....."), reply_to_message_id=rtmid, message_thread_id=dest_thread_id)
            except FloodWait as fw:
                await safe_status_edit(c, uid, p.id, f"⚠️ FloodWait: Telegram blocked upload for {fw.value} seconds.")
                await asyncio.sleep(fw.value + 5)
                if f and os.path.exists(f): 
                    try: os.remove(f)
                    except: pass
                return 'Failed (FloodWait).'
            except Exception as e:
                logger.error(f"Upload failed for {f}: {e}")
                await safe_status_edit(c, uid, p.id, f'Upload failed: {str(e)[:30]}')
                if f and os.path.exists(f): 
                    try: os.remove(f)
                    except: pass
                return 'Failed.'
            
            if f and os.path.exists(f):
                try: os.remove(f)
                except Exception as e: logger.error(f"Failed to safely delete {f}: {e}")
                    
            await c.delete_messages(uid, p.id)
            return 'Done.'
            
        elif m.text:
            proc_text = await process_text_with_rules(uid, orig_text)
            user_cap = await get_user_data_key(uid, 'caption', '')
            raw_caption = f'{proc_text}\n\n{user_cap}' if proc_text and user_cap else user_cap if user_cap else proc_text
            raw_caption = re.sub(r'(?i)Number Of Digits', 'No. of Digit', raw_caption)
            
            if "🎬 Title:" in raw_caption or "📁 Topic:" in raw_caption or "🎬" in raw_caption:
                ft = raw_caption.strip()
            else:
                ft = beautify_caption(raw_caption)
            
            is_restricted = getattr(m.chat, "has_protected_content", False) if m.chat else False
            direct_forward = await get_user_data_key(uid, "direct_forward", False)
            
            if direct_forward and not is_restricted:
                try:
                    client_to_use = u if (lt == 'private' and u) else getattr(m, '_client', c)
                    await client_to_use.copy_message(
                        chat_id=tcid, 
                        from_chat_id=i, 
                        message_id=m.id, 
                        caption=ft if ft else None, 
                        reply_to_message_id=rtmid, 
                        message_thread_id=dest_thread_id
                    )
                    return 'Fast Forwarded ✅'
                except FloodWait as fw:
                    await asyncio.sleep(fw.value + 5)
                except Exception as e:
                    logger.warning(f"Direct Forward Failed for Text {i}:{m.id} -> {e}")
                    pass
            
            await c.send_message(tcid, text=ft if ft else orig_text, reply_to_message_id=rtmid, message_thread_id=dest_thread_id)
            return 'Sent.'
            
    except Exception as e:
        logger.error(f"Process msg error: {e}")
        return f'Error: {str(e)[:50]}'
    finally:
        if p and hasattr(p, 'id'):
            PROGRESS_LINKS.pop(p.id, None)
            LAST_UPDATE_TIME.pop(p.id, None)

@X.on_callback_query(filters.regex("^(run_batch|run_docbatch|run_single|run_cancel|run_fix)$"))
async def direct_batch_execution(c, q):
    uid = q.from_user.id
    cmd = q.data.replace("run_", "")
    
    await q.message.delete()
    
    if cmd == "cancel":
        Z.pop(uid, None)
        FIX_DATA.pop(uid, None)
        if is_user_active(uid):
            await request_batch_cancel(uid)
            await c.send_message(q.message.chat.id, '✅ Cancellation requested. Process will stop soon.', reply_markup=ReplyKeyboardRemove())
        else:
            await c.send_message(q.message.chat.id, 'No active batch process found.', reply_markup=ReplyKeyboardRemove())
        return
        
    if cmd == "fix":
        FIX_DATA[uid] = {"step": "await_corrupt"}
        await c.send_message(q.message.chat.id, "📁 **Manual Repair Mode ON**\n\nAb wo **Corrupted Video** bhejen jise fix karna hai.", reply_markup=cancel_kb)
        return

    if FREEMIUM_LIMIT == 0 and not await is_premium_user(uid):
        return await c.send_message(q.message.chat.id, "This bot does not provide free servies, get subscription from OWNER")
    
    if await sub(c, q.message) == 1: return
    
    pro = await c.send_message(q.message.chat.id, 'Doing some checks hold on...', reply_markup=cancel_kb)
    
    if is_user_active(uid):
        try:
            return await pro.edit_text('You have an active task. Use /stop to cancel it.')
        except Exception:
            return await c.send_message(q.message.chat.id, 'You have an active task. Use /stop to cancel it.')
    
    ubot = await get_ubot(uid)
    if not ubot:
        try:
            return await pro.edit_text('Add your bot with /setbot first')
        except Exception:
            return await c.send_message(q.message.chat.id, 'Add your bot with /setbot first')
    
    Z[uid] = {
        "status": "running",
        'step': 'start' if cmd in ['batch', 'docbatch'] else 'start_single',
        'doc_only': True if cmd == 'docbatch' else False
    }
    msg_text = f'Send {"start link..." if cmd in ["batch", "docbatch"] else "link you to process"}.'
    
    try:
        await pro.edit_text(msg_text)
    except Exception:
        await c.send_message(q.message.chat.id, msg_text, reply_markup=cancel_kb)

@X.on_message(filters.command(['batch', 'single', 'docbatch']))
async def process_cmd(c, m):
    uid = m.from_user.id
    cmd = m.command[0]
    
    if FREEMIUM_LIMIT == 0 and not await is_premium_user(uid):
        await m.reply_text("This bot does not provide free servies, get subscription from OWNER")
        return
    
    if await sub(c, m) == 1: return
    pro = await m.reply_text('Doing some checks hold on...', reply_markup=cancel_kb)
    
    if is_user_active(uid):
        try:
            await pro.edit_text('You have an active task. Use /stop to cancel it.')
        except Exception:
            await m.reply_text('You have an active task. Use /stop to cancel it.')
        return
    
    ubot = await get_ubot(uid)
    if not ubot:
        try:
            await pro.edit_text('Add your bot with /setbot first')
        except Exception:
            await m.reply_text('Add your bot with /setbot first')
        return
    
    Z[uid] = {
        'step': 'start' if cmd in ['batch', 'docbatch'] else 'start_single',
        'doc_only': True if cmd == 'docbatch' else False
    }
    msg_text = f'Send {"start link..." if cmd in ["batch", "docbatch"] else "link you to process"}.'
    
    try:
        await pro.edit_text(msg_text)
    except Exception:
        await m.reply_text(msg_text, reply_markup=cancel_kb)

@X.on_message(filters.command(['cancel', 'stop']))
async def cancel_cmd(c, m):
    uid = m.from_user.id
    Z.pop(uid, None)
    FIX_DATA.pop(uid, None)
    if is_user_active(uid):
        if await request_batch_cancel(uid):
            await m.reply_text('Cancellation requested. The current batch will stop after the current download completes.', reply_markup=ReplyKeyboardRemove())
        else:
            await m.reply_text('Failed to request cancellation. Please try again.', reply_markup=ReplyKeyboardRemove())
    else:
        await m.reply_text('No active batch process found.', reply_markup=ReplyKeyboardRemove())

@X.on_message(filters.text & filters.private & ~login_in_progress & ~filters.regex(r"(?i)^/(?!(s|d|cancel)$)"))
async def text_handler(c, m):
    uid = m.from_user.id
    
    if m.text in ["/cancel", "❌ Cancel"]:
        Z.pop(uid, None)
        FIX_DATA.pop(uid, None)
        return await m.reply_text("🚫 **Process Cancelled.**", reply_markup=ReplyKeyboardRemove())
    
    if uid not in Z:
        if m.text and ("t.me/" in m.text or "telegram.me/" in m.text):
            i, d, lt = E(m.text)
            if not i or not d:
                await m.reply_text('❌ Invalid link format.', reply_markup=cancel_kb)
                return
            
            Z[uid] = {'step': 'count', 'cid': i, 'sid': d, 'lt': lt}
            prompt_msg = await m.reply_text('🔗 **Starting Link Detected!**\n\nAb aap 2 tarike se bata sakte hain:\n1️⃣ **Ending Link bhejen** (Jahan tak extract karna hai)\n👉 *Ya fir*\n2️⃣ **Number bhejen** (Kitne messages nikalne hain, ex: 50)', reply_markup=cancel_kb)
            Z[uid]['last_prompt_id'] = prompt_msg.id
            return
        else:
            return
            
    s = Z.get(uid, {}).get('step')
    if not s:
        return
        
    x = await get_ubot(uid)
    if not x:
        await m.reply("Add your bot /setbot `token`", reply_markup=ReplyKeyboardRemove())
        return

    if s == 'start':
        L = m.text.strip()
        if "t.me/" in L or "telegram.me/" in L:
            i, d, lt = E(L)
            if not i or not d:
                await m.reply_text('Invalid link format.', reply_markup=cancel_kb)
                return
            Z[uid].update({'step': 'count', 'cid': i, 'sid': d, 'lt': lt})
            await m.reply_text('🔗 **Starting Link Detected!**\n\nAb aap 2 tarike se bata sakte hain:\n1️⃣ **Ending Link bhejen** (Jahan tak extract karna hai)\n👉 *Ya fir*\n2️⃣ **Number bhejen** (Kitne messages nikalne hain, ex: 50)', reply_markup=cancel_kb)
        else:
            pt = await m.reply_text("⚙️ Validating Source ID for Full Group Clone...", reply_markup=cancel_kb)
            try:
                chat_identifier = int(L) if L.lstrip('-').isdigit() else L
                uc = await get_uclient(uid)
                ubot = UB.get(uid)
                client_to_use = uc if uc else ubot
                
                if not client_to_use:
                    await pt.edit("❌ Error: Client not connected. Please login first.")
                    return
                    
                chat_info = await client_to_use.get_chat(chat_identifier)
                last_msg_id = 1
                async for msg in client_to_use.get_chat_history(chat_info.id, limit=1):
                    last_msg_id = msg.id
                    break
                    
                maxlimit = PREMIUM_LIMIT if await is_premium_user(uid) else FREEMIUM_LIMIT
                total_to_clone = min(last_msg_id, maxlimit)
                
                Z[uid].update({
                    'step': 'ask_remove_words',
                    'cid': str(chat_info.id),
                    'sid': 1,
                    'num': total_to_clone,
                    'lt': 'private' if str(chat_info.id).startswith('-100') else 'public'
                })
                await asyncio.sleep(2)
                await m.reply_text("📝 **Step 1/4: Words to Remove**\nEnter words you want to remove from caption (comma separated).\n\n🔹 Type `/d` for Default (Settings wale)\n🔹 Type `0` for Previous (Pichle batch wale)\n🔹 Type `/s` to Skip", reply_markup=cancel_kb)
                return
            except Exception as e:
                Z.pop(uid, None)
                await pt.edit(f"❌ **Error:** Invalid Chat ID ya fir aapka bot/account us channel ka member nahi hai.\n\n`{str(e)[:50]}`")
                return

    elif s == 'start_single':
        L = m.text
        i, d, lt = E(L)
        if not i or not d:
            await m.reply_text('❌ Invalid link format.', reply_markup=cancel_kb)
            return
            
        Z[uid].update({'step': 'ask_remove_words', 'cid': i, 'sid': d, 'num': 1, 'lt': lt})
        
        try:
            msgs_to_del = [m.id]
            if Z[uid].get('last_prompt_id'): msgs_to_del.append(Z[uid]['last_prompt_id'])
            await c.delete_messages(m.chat.id, msgs_to_del)
        except: pass
        
        prompt_msg = await m.reply_text("📝 **Step 1/4: Words to Remove**\nEnter words you want to remove from caption (comma separated).\n\n🔹 Type `/d` for Default (Settings wale)\n🔹 Type `0` for Previous (Pichle batch wale)\n🔹 Type `/s` to Skip", reply_markup=cancel_kb)
        Z[uid]['last_prompt_id'] = prompt_msg.id
        return

    elif s == 'count':
        maxlimit = PREMIUM_LIMIT if await is_premium_user(uid) else FREEMIUM_LIMIT
        
        if m.text.isdigit(): count = int(m.text)
        else:
            end_i, end_d, end_lt = E(m.text)
            if not end_i or not end_d: 
                await m.reply_text('❌ Please enter a valid number or a valid Telegram ending link.', reply_markup=cancel_kb)
                return
            start_d = int(Z[uid]['sid'])
            end_d = int(end_d)
            if str(end_i) != str(Z[uid]['cid']): 
                await m.reply_text('❌ Ending link usi channel/group ka hona chahiye jiska starting link tha!', reply_markup=cancel_kb)
                return
            if end_d < start_d: 
                await m.reply_text('❌ Ending ID starting ID se bada hona chahiye!', reply_markup=cancel_kb)
                return
            count = (end_d - start_d) + 1

        if count > maxlimit: 
            await m.reply_text(f'❌ Maximum limit is {maxlimit}.', reply_markup=cancel_kb)
            return

        Z[uid].update({'step': 'ask_remove_words', 'num': count})
        
        try:
            msgs_to_del = [m.id]
            if Z[uid].get('last_prompt_id'): msgs_to_del.append(Z[uid]['last_prompt_id'])
            await c.delete_messages(m.chat.id, msgs_to_del)
        except: pass
        
        prompt_msg = await m.reply_text("📝 **Step 1/4: Words to Remove**\nEnter words you want to remove from caption (comma separated).\n\n🔹 Type `/d` for Default (Settings wale)\n🔹 Type `0` for Previous (Pichle batch wale)\n🔹 Type `/s` to Skip", reply_markup=cancel_kb)
        Z[uid]['last_prompt_id'] = prompt_msg.id
        return

    elif s == 'ask_remove_words':
        text_lower = m.text.strip().lower()
        if text_lower in ['/d', 'd']: Z[uid]['custom_remove'] = "DEFAULT"
        elif text_lower == '0': Z[uid]['custom_remove'] = "PREVIOUS"
        elif text_lower in ['/s', 's']: Z[uid]['custom_remove'] = "SKIP"
        else: Z[uid]['custom_remove'] = [w.strip() for w in m.text.strip().split(',')]
        
        Z[uid]['step'] = 'ask_replace_words'
        
        try:
            msgs_to_del = [m.id]
            if Z[uid].get('last_prompt_id'): msgs_to_del.append(Z[uid]['last_prompt_id'])
            await c.delete_messages(m.chat.id, msgs_to_del)
        except: pass
        
        prompt_msg = await m.reply_text("🔄 **Step 2/4: Words to Replace**\nEnter words to rename. Format: `old_word | new_word`\n\n🔹 Type `/d` for Default\n🔹 Type `0` for Previous\n🔹 Type `/s` to Skip", reply_markup=cancel_kb)
        Z[uid]['last_prompt_id'] = prompt_msg.id
        return

    elif s == 'ask_replace_words':
        text_lower = m.text.strip().lower()
        if text_lower in ['/d', 'd']: Z[uid]['custom_replace'] = "DEFAULT"
        elif text_lower == '0': Z[uid]['custom_replace'] = "PREVIOUS"
        elif text_lower in ['/s', 's']: Z[uid]['custom_replace'] = "SKIP"
        else:
            try:
                pairs = m.text.strip().split(',')
                r_dict = {}
                for p in pairs:
                    if '|' in p:
                        o, nw = p.split('|', 1)
                        r_dict[o.strip()] = nw.strip()
                Z[uid]['custom_replace'] = r_dict
            except: Z[uid]['custom_replace'] = {}
            
        Z[uid]['step'] = 'ask_watermark'
        
        try:
            msgs_to_del = [m.id]
            if Z[uid].get('last_prompt_id'): msgs_to_del.append(Z[uid]['last_prompt_id'])
            await c.delete_messages(m.chat.id, msgs_to_del)
        except: pass
        
        prompt_msg = await m.reply_text("🖼️ **Step 3/4: Thumbnail Watermark**\nEnter the text for Video Watermark.\n\n🔹 Type `/d` for Default\n🔹 Type `0` for Previous\n🔹 Type `/s` to Skip", reply_markup=cancel_kb)
        Z[uid]['last_prompt_id'] = prompt_msg.id
        return

    elif s == 'ask_watermark':
        text_lower = m.text.strip().lower()
        if text_lower in ['/d', 'd']: Z[uid]['custom_wm'] = "DEFAULT"
        elif text_lower == '0': Z[uid]['custom_wm'] = "PREVIOUS"
        elif text_lower in ['/s', 's']: Z[uid]['custom_wm'] = "SKIP"
        else: Z[uid]['custom_wm'] = m.text.strip()
        
        Z[uid]['step'] = 'ask_target_chat'
        
        try:
            msgs_to_del = [m.id]
            if Z[uid].get('last_prompt_id'): msgs_to_del.append(Z[uid]['last_prompt_id'])
            await c.delete_messages(m.chat.id, msgs_to_del)
        except: pass
        
        prompt_msg = await m.reply_text("🎯 **Step 4/4: Target Channel ID**\nEnter the Chat ID where you want to send files (e.g., -100123456).\n\n🔹 Type `/d` for Default Chat ID\n🔹 Type `0` for Previous Chat ID", reply_markup=cancel_kb)
        Z[uid]['last_prompt_id'] = prompt_msg.id
        return

    elif s == 'ask_target_chat':
        text_lower = m.text.strip().lower()
        if text_lower in ['/d', 'd']: Z[uid]['custom_chat'] = "DEFAULT"
        elif text_lower == '0': Z[uid]['custom_chat'] = "PREVIOUS"
        else: Z[uid]['custom_chat'] = m.text.strip()
        
        Z[uid]['step'] = 'process'

        i, s_id, n, lt = Z[uid]['cid'], Z[uid]['sid'], Z[uid]['num'], Z[uid]['lt']
        success = 0
        
        try:
            msgs_to_del = [m.id]
            if Z[uid].get('last_prompt_id'): msgs_to_del.append(Z[uid]['last_prompt_id'])
            await c.delete_messages(m.chat.id, msgs_to_del)
        except: pass
        
        pt = await c.send_message(m.chat.id, '⚙️ Validating inputs and starting batch...', reply_markup=ReplyKeyboardRemove())
        
        async def safe_pt_edit_init(text_msg):
            nonlocal pt
            try: await pt.edit_text(text_msg)
            except Exception:
                try: pt = await c.send_message(uid, text_msg)
                except Exception: pass
        
        uc = await get_uclient(uid)
        ubot = await get_ubot(uid)
        if not uc or not ubot: return await safe_pt_edit_init('Missing client setup')
        if is_user_active(uid): return await safe_pt_edit_init('Active task exists')

        if Z[uid]['custom_remove'] == "DEFAULT":
            resolved_remove = await get_user_data_key(uid, "delete_words", [])
        elif Z[uid]['custom_remove'] == "PREVIOUS":
            resolved_remove = await get_user_data_key(uid, "last_remove", [])
        elif Z[uid]['custom_remove'] == "SKIP":
            resolved_remove = []
        else:
            resolved_remove = Z[uid]['custom_remove']
            await save_user_data(uid, "last_remove", resolved_remove)

        if Z[uid]['custom_replace'] == "DEFAULT":
            resolved_replace = await get_user_data_key(uid, "replacement_words", {})
        elif Z[uid]['custom_replace'] == "PREVIOUS":
            resolved_replace = await get_user_data_key(uid, "last_replace", {})
        elif Z[uid]['custom_replace'] == "SKIP":
            resolved_replace = {}
        else:
            resolved_replace = Z[uid]['custom_replace']
            await save_user_data(uid, "last_replace", resolved_replace)

        if Z[uid]['custom_wm'] == "DEFAULT":
            resolved_wm = await get_user_data_key(uid, "watermark", "")
        elif Z[uid]['custom_wm'] == "PREVIOUS":
            resolved_wm = await get_user_data_key(uid, "last_wm", "")
        elif Z[uid]['custom_wm'] == "SKIP":
            resolved_wm = "skip"
        else:
            resolved_wm = Z[uid]['custom_wm']
            await save_user_data(uid, "last_wm", resolved_wm)

        if Z[uid]['custom_chat'] == "DEFAULT":
            cfg_chat = await get_user_data_key(uid, 'chat_id', None)
            if cfg_chat: 
                Z[uid]['custom_chat'] = str(cfg_chat)
            else:
                Z[uid]['custom_chat'] = str(m.chat.id)
        elif Z[uid]['custom_chat'] == "PREVIOUS":
            last_chat = await get_user_data_key(uid, "last_chat", str(m.chat.id))
            Z[uid]['custom_chat'] = str(last_chat)
        else:
            await save_user_data(uid, "last_chat", str(Z[uid]['custom_chat']))

        source_id_raw = Z[uid]['cid']
        dest_id_str = str(Z[uid]['custom_chat'])
        target_chat_id = dest_id_str.split('/')[0] if '/' in dest_id_str else dest_id_str

        source_name = str(source_id_raw)
        dest_name = str(target_chat_id)

        try:
            c_id = str(source_id_raw)
            parsed_cid = int(c_id) if c_id.lstrip('-').isdigit() else c_id
            
            first_msg = await uc.get_messages(parsed_cid, int(Z[uid]['sid']))
            if first_msg and first_msg.chat and first_msg.chat.title:
                source_name = first_msg.chat.title
        except Exception as e:
            pass
            
        try:
            d_id = str(target_chat_id)
            parsed_did = int(d_id) if d_id.lstrip('-').isdigit() else d_id
            
            dest_chat = await ubot.get_chat(parsed_did)
            if dest_chat and dest_chat.title:
                dest_name = dest_chat.title
        except Exception:
            pass

        task_data = {
            "source": source_name,
            "destination": dest_name,
            "source_id": str(source_id_raw),
            "dest_id": str(Z[uid]['custom_chat']),  
            "remove_list": resolved_remove,
            "replace_dict": resolved_replace,
            "watermark": resolved_wm,
            "total": n,            
            "success": 0,          
            "status": "running",
            "doc_only": Z[uid].get('doc_only', False)
        }
        
        await db["tasks"].update_one({"user_id": uid}, {"$set": task_data}, upsert=True)

        Z[uid]['task_data'] = task_data
        Z[uid]['pt'] = pt
        
        from plugins.smart_preview import send_smart_preview
        await send_smart_preview(c, uid, Z, UB, UC)
        return

    elif s == 'wait_for_manual_caption':
        manual_cap = m.text.markdown
        Z[uid]['task_data']['manual_caption'] = manual_cap
        await db["tasks"].update_one({"user_id": uid}, {"$set": {"manual_caption": manual_cap}})
        
        pt = Z[uid]['pt']
        try: await pt.edit_text("✅ **Custom caption saved!**\n\n🚀 Starting batch extraction process now...")
        except: pt = await m.reply_text("✅ **Custom caption saved!**\n\n🚀 Starting batch extraction process now...")
        Z[uid]['pt'] = pt
        
        await start_actual_batch(c, uid)
        return

USER_LOCKS = {}
def get_user_lock(uid):
    if uid not in USER_LOCKS:
        import asyncio
        USER_LOCKS[uid] = asyncio.Lock()
    return USER_LOCKS[uid]

async def start_actual_batch(c, uid):
    if uid not in Z: return
    i, s_id, n, lt = Z[uid]['cid'], Z[uid]['sid'], Z[uid]['num'], Z[uid]['lt']
    task_data = Z[uid]['task_data']
    pt = Z[uid]['pt']
    
    dest_id_str = str(task_data['dest_id'])
    force_thread_id = None
    if '/' in dest_id_str:
        target_chat_id = int(dest_id_str.split('/')[0])
        force_thread_id = int(dest_id_str.split('/')[1])
    else:
        target_chat_id = int(dest_id_str)

    success = 0
    source_name = task_data.get('source', str(i))
    dest_name = task_data.get('destination', str(target_chat_id))
    
    uc = await get_uclient(uid)
    ubot = await get_ubot(uid)

    async def safe_pt_edit(text_msg):
        nonlocal pt
        try:
            await pt.edit_text(text_msg)
        except Exception:
            try:
                pt = await c.send_message(uid, text_msg)
                Z[uid]['pt'] = pt 
            except Exception:
                pass
    
    await add_active_batch(uid, {"total": n, "current": 0, "success": 0, "source": str(i), "destination": str(target_chat_id), "cancel_requested": False, "progress_message_id": pt.id})
    topic_map = {}
    
    ubot_status_msg = None
    if ubot:
        try:
            ubot_status_msg = await ubot.send_message(
                uid, 
                f"🚀 **Batch Started!**\n\n📢 **From:** `{source_name}`\n🎯 **To:** `{dest_name}`\n📦 **Total Files:** {n}\n\n🔄 Progress updates will appear here every 10 seconds..."
            )
        except Exception: pass

    last_ubot_update_time = time.time()
    batch_start_time = time.time()

    # ========================================================
    # 🔥 BULK MODE DETECTION ENGINE (ULTRA-SMART) 🔥
    # ========================================================
    direct_forward = await get_user_data_key(uid, "direct_forward", False)
    remove_list = task_data.get("remove_list", [])
    replace_dict = task_data.get("replace_dict", {})
    doc_only = task_data.get("doc_only", False)
    skip_ai = task_data.get("skip_ai", False)
    
    # Check if Watermark is purely bypassed/skipped
    watermark = str(task_data.get("watermark", "")).strip().lower()
    wm_skipped = (watermark == "skip") or (watermark == "")
    if watermark == "default":
        cfg_wm = await get_user_data_key(uid, "watermark", "")
        wm_skipped = not bool(cfg_wm.strip())
    
    is_restricted = False
    try:
        client_to_check = uc if uc else ubot
        if client_to_check:
            chat_info = await client_to_check.get_chat(i)
            is_restricted = getattr(chat_info, "has_protected_content", False)
    except:
        pass
        
    client_to_use_for_bulk = uc if (lt == 'private' and uc) else (ubot if ubot else c)
    has_bulk_func = hasattr(client_to_use_for_bulk, "copy_messages")
    has_text_rules = bool(remove_list or replace_dict)
    
    is_bulk_eligible = False
    
    # 🔴 Strict Golden Rule For Bulk Forwarding:
    # Everything MUST be skipped or empty (including watermark).
    if direct_forward and not has_text_rules and not is_restricted and not doc_only and wm_skipped and n > 1:
        if skip_ai:
            is_bulk_eligible = True
        else:
            try:
                first_msg_check = await get_msg(ubot, uc, i, int(s_id), lt)
                if first_msg_check and not getattr(first_msg_check, "caption", None) and not getattr(first_msg_check, "text", None):
                    is_bulk_eligible = True
            except:
                pass

    try:
        if is_bulk_eligible:
            # 🚀 THE 10-BY-10 BULK ENGINE
            await safe_pt_edit(f"🚀 **Bulk Engine Activated (10-by-10) ⚡**\n\n📢 **From:** `{source_name}`\n📦 **Total:** {n} files\n\n🤖 **Fast mode enabled. Check Custom Bot for live progress!**")
            
            all_ids = [int(s_id) + x for x in range(n)]
            chunks = [all_ids[k:k+10] for k in range(0, len(all_ids), 10)]
            
            for chunk_idx, chunk in enumerate(chunks):
                # 🛡️ THE FIX: Safe Modulo Check based on Chunk Index (1000 files)
                processed_count = chunk_idx * 10
                if processed_count > 0 and processed_count % 1000 == 0:
                    if ubot_status_msg:
                        try: await ubot_status_msg.edit_text(f'💤 **Anti-Ban Shield Active!**\n1000 files processed. Taking a 3-minute break to prevent Telegram API Ban...')
                        except: pass
                    await asyncio.sleep(180) # 3 Min Sleep
                
                if time.time() - batch_start_time > 10800:
                    break_dur = random.uniform(1150.5, 1250.2)
                    if ubot_status_msg:
                        try: await ubot_status_msg.edit_text(f'💤 **Anti-Ban Break!**\nTaking a {int(break_dur/60)} min break to secure account...')
                        except Exception: pass
                    await asyncio.sleep(break_dur)
                    batch_start_time = time.time()
                
                if should_cancel(uid):
                    break
                
                await update_batch_progress(uid, min(n, (chunk_idx * 10) + 10), success)
                
                user_lock = get_user_lock(uid)
                await user_lock.acquire()
                try:
                    dest_thread_id = force_thread_id
                    if not dest_thread_id:
                        for msg_id in chunk:
                            first_msg = await get_msg(ubot, uc, i, msg_id, lt)
                            if first_msg:
                                src_thread_id = getattr(first_msg, "message_thread_id", None) or getattr(first_msg, "reply_to_message_id", None)
                                if src_thread_id:
                                    if src_thread_id not in topic_map:
                                        cached_topic = None
                                        if topic_cache_col is not None: cached_topic = await topic_cache_col.find_one({"source_chat_id": str(i), "source_thread_id": src_thread_id, "target_chat_id": str(target_chat_id)})
                                        if cached_topic: topic_map[src_thread_id] = cached_topic["dest_thread_id"]
                                        else:
                                            try:
                                                from pyrogram.raw.functions.channels import GetForumTopicsByID
                                                client_to_use = getattr(first_msg, '_client', uc if uc else ubot)
                                                try: await client_to_use.get_chat(i)
                                                except: pass
                                                peer = await client_to_use.resolve_peer(i)
                                                topic_data = await client_to_use.invoke(GetForumTopicsByID(channel=peer, topics=[src_thread_id]))
                                                topic_title = topic_data.topics[0].title if (topic_data and getattr(topic_data, "topics", None)) else f"Extracted Topic {src_thread_id}"
                                            except Exception: topic_title = f"Backup Topic {src_thread_id}"
                                            try:
                                                try: await ubot.get_chat(target_chat_id)
                                                except: pass
                                                new_topic = await ubot.create_forum_topic(chat_id=target_chat_id, title=topic_title)
                                                new_dest_id = getattr(new_topic, "message_thread_id", getattr(new_topic, "id", None))
                                                topic_map[src_thread_id] = new_dest_id
                                                if new_dest_id and topic_cache_col is not None: await topic_cache_col.insert_one({"source_chat_id": str(i), "source_thread_id": src_thread_id, "target_chat_id": str(target_chat_id), "dest_thread_id": new_dest_id})
                                            except Exception: topic_map[src_thread_id] = None
                                    dest_thread_id = topic_map.get(src_thread_id)
                                break 
                                
                    if has_bulk_func:
                        copied = await client_to_use_for_bulk.copy_messages(
                            chat_id=target_chat_id,
                            from_chat_id=i,
                            message_ids=chunk,
                            reply_to_message_id=dest_thread_id 
                        )
                        success += len(copied)
                    else:
                        for msg_id in chunk:
                            try:
                                await client_to_use_for_bulk.copy_message(
                                    chat_id=target_chat_id,
                                    from_chat_id=i,
                                    message_id=msg_id,
                                    reply_to_message_id=dest_thread_id
                                )
                                success += 1
                            except FloodWait as fw:
                                await asyncio.sleep(fw.value + 5)
                            except Exception:
                                pass
                    
                    await db["tasks"].update_one({"user_id": uid}, {"$set": {"success": success}})
                    
                    try:
                        percentage = int(((chunk_idx + 1) * 10 / n) * 100)
                        if percentage > 100: percentage = 100
                        await db["live_status"].update_one(
                            {"user_id": uid},
                            {"$set": {
                                "source": source_name, "source_id": str(i), "destination": dest_name, "dest_id": str(target_chat_id),
                                "current": min((chunk_idx + 1) * 10, n), "total": n, "percentage": percentage
                            }},
                            upsert=True
                        )
                    except Exception: pass
                    
                    await asyncio.sleep(random.uniform(3.5, 6.2))
                    
                except FloodWait as fw:
                    await asyncio.sleep(fw.value + 5)
                except Exception as e:
                    logger.error(f"Bulk Chunk error: {e}")
                    await asyncio.sleep(2)
                finally:
                    user_lock.release()
                    
                if time.time() - last_ubot_update_time >= 10:
                    if ubot_status_msg:
                        percent = round((min(n, (chunk_idx + 1) * 10) / n) * 100, 2)
                        try:
                            await ubot_status_msg.edit_text(
                                f"📊 **Batch Progress (Bulk Mode ⚡)**\n\n📢 **From:** `{source_name}`\n📦 **Processed:** {min(n, (chunk_idx + 1) * 10)}/{n} ({percent}%)\n✅ **Success:** {success}\n🚀 **Speed:** 10x Fast Forward\n\n⏳ Process running smoothly..."
                            )
                        except Exception: pass
                    last_ubot_update_time = time.time()

        else:
            # ⚙️ THE STANDARD ENGINE (1-by-1)
            await safe_pt_edit(f"⚙️ **Standard Mode Activated (1-by-1)**\n\n📢 **From:** `{source_name}`\n📦 **Total:** {n} files\n\n🤖 **Check Custom Bot for live progress!**")
            
            for j in range(n):
                # 🛡️ THE FIX: Anti-Ban logic safe placement (1000 files)
                if j > 0 and j % 1000 == 0:
                    if ubot_status_msg:
                        try: await ubot_status_msg.edit_text(f'💤 **Anti-Ban Shield Active!**\n1000 files processed. Taking a 3-minute break to prevent Telegram API Ban...')
                        except: pass
                    await asyncio.sleep(180) # 3 Min Sleep
                
                if time.time() - batch_start_time > 10800:
                    break_dur = random.uniform(1150.5, 1250.2)
                    if ubot_status_msg:
                        try: await ubot_status_msg.edit_text(f'💤 **Anti-Ban Break!**\nLagatar 3 ghante se process chal raha hai. {int(break_dur/60)} min ka break le raha hu...')
                        except Exception: pass
                    await asyncio.sleep(break_dur)
                    batch_start_time = time.time()
                
                if should_cancel(uid):
                    break
                
                await update_batch_progress(uid, j, success)
                mid = int(s_id) + j
                max_retries = 3
                res = None
                
                user_lock = get_user_lock(uid)
                await user_lock.acquire() 
                try:
                    for attempt in range(max_retries):
                        try:
                            msg = await get_msg(ubot, uc, i, mid, lt)
                            if msg:
                                dest_thread_id = force_thread_id
                                src_thread_id = getattr(msg, "message_thread_id", None) or getattr(msg, "reply_to_message_id", None)
                                
                                if not dest_thread_id and src_thread_id:
                                    if src_thread_id not in topic_map:
                                        cached_topic = None
                                        if topic_cache_col is not None: cached_topic = await topic_cache_col.find_one({"source_chat_id": str(i), "source_thread_id": src_thread_id, "target_chat_id": str(target_chat_id)})
                                        if cached_topic: topic_map[src_thread_id] = cached_topic["dest_thread_id"]
                                        else:
                                            try:
                                                from pyrogram.raw.functions.channels import GetForumTopicsByID
                                                client_to_use = getattr(msg, '_client', uc if uc else ubot)
                                                try: await client_to_use.get_chat(i)
                                                except: pass
                                                peer = await client_to_use.resolve_peer(i)
                                                topic_data = await client_to_use.invoke(GetForumTopicsByID(channel=peer, topics=[src_thread_id]))
                                                topic_title = topic_data.topics[0].title if (topic_data and getattr(topic_data, "topics", None)) else f"Extracted Topic {src_thread_id}"
                                            except Exception: topic_title = f"Backup Topic {src_thread_id}"
                                            try:
                                                try: await ubot.get_chat(target_chat_id)
                                                except: pass
                                                new_topic = await ubot.create_forum_topic(chat_id=target_chat_id, title=topic_title)
                                                new_dest_id = getattr(new_topic, "message_thread_id", getattr(new_topic, "id", None))
                                                topic_map[src_thread_id] = new_dest_id
                                                if new_dest_id and topic_cache_col is not None: await topic_cache_col.insert_one({"source_chat_id": str(i), "source_thread_id": src_thread_id, "target_chat_id": str(target_chat_id), "dest_thread_id": new_dest_id})
                                            except Exception: topic_map[src_thread_id] = None
                                    dest_thread_id = topic_map.get(src_thread_id)
                                
                                res = await process_msg(ubot, uc, msg, target_chat_id, lt, uid, i, task=task_data, dest_thread_id=dest_thread_id)
                                if res and isinstance(res, str) and any(x in res for x in ['Done', 'Copied', 'Sent', 'Forwarded']):
                                    success += 1
                                    await db["tasks"].update_one({"user_id": uid}, {"$set": {"success": success}})
                                    try:
                                        percentage = int(((j + 1) / n) * 100)
                                        await db["live_status"].update_one(
                                            {"user_id": uid},
                                            {"$set": {
                                                "source": source_name, "source_id": str(i), "destination": dest_name, "dest_id": str(target_chat_id),
                                                "current": j + 1, "total": n, "percentage": percentage
                                            }},
                                            upsert=True
                                        )
                                    except Exception: pass
                                    break 
                                else:
                                    if attempt < max_retries - 1:
                                        await asyncio.sleep(5) 
                                        continue
                                    else: break 
                            else:
                                skip_delay = random.uniform(2.1, 5.4)
                                await asyncio.sleep(skip_delay)
                                break 
                        except Exception as e:
                            if attempt < max_retries - 1: await asyncio.sleep(5)
                finally:
                    user_lock.release() 

                if n > 1 and (res and isinstance(res, str) and any(x in res for x in ['Done', 'Copied', 'Sent', 'Forwarded'])):
                    if 'Fast Forwarded' in res:
                        delay_time = random.uniform(1.1, 3.4)
                    else:
                        delay_time = random.uniform(17.5, 35.8)
                    await asyncio.sleep(delay_time)

                if time.time() - last_ubot_update_time >= 10:
                    if ubot_status_msg:
                        percent = round(((j + 1) / n) * 100, 2)
                        mode_str = 'Fast Forward ⏩' if (res and 'Fast Forwarded' in res) else 'Download & Upload ⬇️'
                        try:
                            await ubot_status_msg.edit_text(
                                f"📊 **Batch Progress (Standard Mode)**\n\n📢 **From:** `{source_name}`\n📦 **Processed:** {j + 1}/{n} ({percent}%)\n✅ **Success:** {success}\n🚀 **Last Action:** {mode_str}\n\n⏳ Process running smoothly..."
                            )
                        except Exception: pass
                    last_ubot_update_time = time.time()

        # 🔥 COMMON SUCCESS NOTIFICATION 🔥
        if not should_cancel(uid):
            try: await c.send_message(uid, f'✅ **Batch Completed!**\n📊 Successfully Processed: {success}/{n}\n🎯 Sent to Chat ID: `{target_chat_id}`')
            except: pass
            
            if ubot_status_msg:
                try: await ubot_status_msg.edit_text(f"🎉 **Batch Completed!**\n\n✅ **Success:** {success}/{n} files\n🎯 **Destination:** `{target_chat_id}`")
                except Exception: pass
                
            try:
                from datetime import datetime
                admin_name = await get_user_data_key(uid, "admin_name", "Admin") 
                await db["admin_logs"].insert_one({"admin_id": uid, "admin_name": admin_name, "action": f"Batch Cloned: {success} files", "target": f"From {source_name} ➔ {dest_name}", "timestamp": datetime.now()})
            except Exception: pass
        else:
            if ubot_status_msg:
                try: await ubot_status_msg.edit_text(f'🛑 **Process Cancelled by User!**\n\n✅ **Success:** {success}/{n} files')
                except: pass
            
    finally:
        await remove_active_batch(uid)
        Z.pop(uid, None)
        if uid in UC:
            try: await UC[uid].stop()
            except Exception: pass
            finally: UC.pop(uid, None)
        ref_file = f"temp_reference_{uid}.mp4"
        if os.path.exists(ref_file):
            try: os.remove(ref_file)
            except Exception: pass
        
        try:
            from datetime import datetime
            await db["history"].insert_one({
                "user_id": uid,
                "source": source_name,
                "source_id": str(i),
                "destination": dest_name,
                "dest_id": str(target_chat_id),
                "count": success,
                "timestamp": datetime.now()
            })
            await db["live_status"].delete_one({"user_id": uid}) 
        except Exception: pass

@X.on_message(filters.command("fix") & filters.private)
async def fix_command_handler(c, m):
    uid = m.from_user.id
    FIX_DATA[uid] = {"step": "await_corrupt"}
    await m.reply_text("📁 **Manual Repair Mode ON**\n\nAb wo **Corrupted Video** bhejen jise fix karna hai.", reply_markup=cancel_kb)

@X.on_message(filters.video & filters.private)
async def manual_fix_media_handler(c, m):
    uid = m.from_user.id
    if uid not in FIX_DATA: return 
    step = FIX_DATA[uid].get("step")

    if step == "await_corrupt":
        FIX_DATA[uid]["corrupt_msg"] = m
        FIX_DATA[uid]["caption"] = m.caption.markdown if m.caption else ""
        FIX_DATA[uid]["step"] = "await_reference"
        await m.reply_text("✅ Corrupted video received.\n\nAb wo **Reference Video** bhejen jiska header copy karna hai.", reply_markup=cancel_kb)

    elif step == "await_reference":
        status = await m.reply_text("⏳ Repairing process started...", reply_markup=ReplyKeyboardRemove())
        corrupt_msg = FIX_DATA[uid]["corrupt_msg"]
        ref_msg = m
        caption = FIX_DATA[uid]["caption"]
        corrupt_path, ref_path = f"manual_corrupt_{uid}.mp4", f"manual_ref_{uid}.mp4"

        try:
            await status.edit_text("📥 Downloading Corrupted Video...")
            c_file = await corrupt_msg.download(file_name=corrupt_path)
            await status.edit_text("📥 Downloading Reference Video...")
            r_file = await ref_msg.download(file_name=ref_path)
            await status.edit_text("🛠 Repairing video...")
            fixed_file = await copy_header_and_repair(c_file, r_file)

            if fixed_file and os.path.exists(fixed_file):
                await status.edit_text("📤 Uploading Fixed Video...")
                mtd = await get_video_metadata(fixed_file)
                await c.send_video(chat_id=m.chat.id, video=fixed_file, caption=caption, width=mtd['width'], height=mtd['height'], duration=mtd['duration'])
                await status.delete()
            else:
                await status.edit_text("❌ Repair Failed! Reference video match nahi ho raha hai.")
        except Exception as e:
            await status.edit_text(f"❌ Error: {str(e)}")
        finally:
            for f in [corrupt_path, ref_path]:
                if os.path.exists(f): os.remove(f)
            FIX_DATA.pop(uid, None)