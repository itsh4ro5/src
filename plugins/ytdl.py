import yt_dlp
import os
import tempfile
import time
import asyncio
import random
import string
import requests
import logging
import time
import math
from shared_client import client, app
from telethon import events
from telethon.tl.custom import Button
from utils.db import get_user_cookie
from telethon.sync import TelegramClient
from telethon.tl.types import DocumentAttributeVideo
from utils.func import get_video_metadata, screenshot
from telethon.tl.functions.messages import EditMessageRequest
from devgagantools import fast_upload
from concurrent.futures import ThreadPoolExecutor
import aiohttp 
import logging
import aiofiles
from config import YT_COOKIES, INSTA_COOKIES
from mutagen.id3 import ID3, TIT2, TPE1, COMM, APIC
from mutagen.mp3 import MP3
from utils.func import IS_PAUSED
 
logger = logging.getLogger(__name__)
 
thread_pool = ThreadPoolExecutor()
ongoing_downloads = {}
TEMP_URLS = {}
 
def d_thumbnail(thumbnail_url, save_path):
    try:
        response = requests.get(thumbnail_url, stream=True)
        response.raise_for_status()
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return save_path
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to download thumbnail: {e}")
        return None
 
async def download_thumbnail_async(url, path):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                with open(path, 'wb') as f:
                    f.write(await response.read())
 
async def extract_audio_async(ydl_opts, url):
    def sync_extract():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=True)
    return await asyncio.get_event_loop().run_in_executor(thread_pool, sync_extract)
 
def get_random_string(length=7):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length)) 
 
async def process_audio(client, event, url, platform=None):
    user_id = event.sender_id
    cookies = None
    if platform:
        cookies = await get_user_cookie(user_id, platform)
        if not cookies:
            await event.reply(f"**❌ Aapne {platform.upper()} ki cookies add nahi ki hain.**\nPehle cookies.txt file bhejkar `/addcookie {platform}` reply karein.")
            return
 
    temp_cookie_path = None
    if cookies:
        with tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8', suffix='.txt') as temp_cookie_file:
            temp_cookie_file.write(cookies)
            temp_cookie_path = temp_cookie_file.name
 
    start_time = time.time()
    random_filename = f"@team_spy_pro_{event.sender_id}"
    download_path = f"{random_filename}.mp3"
 
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': f"{random_filename}.%(ext)s",
        'cookiefile': temp_cookie_path,
        'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
        'quiet': False,
        'noplaylist': True,
        'nocheckcertificate': True,
        'legacyserverconnect': True,
    }
    prog = None
 
    progress_message = await event.reply("**__Starting audio extraction...__**")
 
    try:
        info_dict = await extract_audio_async(ydl_opts, url)
        title = info_dict.get('title', 'Extracted Audio')
 
        await progress_message.edit("**__Editing metadata...__**")
 
        if os.path.exists(download_path):
            def edit_metadata():
                audio_file = MP3(download_path, ID3=ID3)
                try:
                    audio_file.add_tags()
                except Exception:
                    pass
                audio_file.tags["TIT2"] = TIT2(encoding=3, text=title)
                audio_file.tags["TPE1"] = TPE1(encoding=3, text="🇮‌🇹‌'🇸‌ 🇭‌4️⃣🇷‌")
                audio_file.tags["COMM"] = COMM(encoding=3, lang="eng", desc="Comment", text="Processed by 🇮‌🇹‌'🇸‌ 🇭‌4️⃣🇷‌")
 
                thumbnail_url = info_dict.get('thumbnail')
                if thumbnail_url:
                    thumbnail_path = os.path.join(tempfile.gettempdir(), "thumb.jpg")
                    asyncio.run(download_thumbnail_async(thumbnail_url, thumbnail_path))
                    with open(thumbnail_path, 'rb') as img:
                        audio_file.tags["APIC"] = APIC(
                            encoding=3, mime='image/jpeg', type=3, desc='Cover', data=img.read()
                        )
                    os.remove(thumbnail_path)
                audio_file.save()
 
            await asyncio.to_thread(edit_metadata)
         
        chat_id = event.chat_id
        if os.path.exists(download_path):
            await progress_message.delete()
            prog = await client.send_message(chat_id, "**__Starting Upload...__**")
            uploaded = await fast_upload(
                client, download_path, 
                reply=prog, 
                name=None,
                progress_bar_function=lambda done, total: progress_callback(done, total, chat_id)
            )
            await client.send_file(chat_id, uploaded, caption=f"**{title}**\n\n**__Powered by 🇮‌🇹‌'🇸‌ 🇭‌4️⃣🇷‌__**")
            if prog:
                await prog.delete()
        else:
            await event.reply(f"**❌ Server blocked the download (IP/SSL Error).**\n\n**🎧 Direct Link se sunein:**\n{url}")
 
    except Exception as e:
        logger.exception("Error during audio extraction or upload")
        await event.reply(f"**❌ Audio extract fail ho gaya.**\n\n**🎧 Direct Link se sunein:**\n{url}")
    finally:
        if os.path.exists(download_path):
            os.remove(download_path)
        if temp_cookie_path and os.path.exists(temp_cookie_path):
            os.remove(temp_cookie_path)

async def fetch_video_info(url, ydl_opts, progress_message, check_duration_and_size):
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=False)
        if check_duration_and_size:
            duration = info_dict.get('duration', 0)
            if duration and duration > 3 * 3600:   
                await progress_message.edit("**❌ __Video is longer than 3 hours. Download aborted...__**")
                return None
            estimated_size = info_dict.get('filesize_approx', 0)
            if estimated_size and estimated_size > 2 * 1024 * 1024 * 1024:   
                await progress_message.edit("**🤞 __Video size is larger than 2GB. Aborting download.__**")
                return None
        return info_dict
 
def download_video(url, ydl_opts):
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
 
@client.on(events.NewMessage(pattern="/dl"))
async def smart_dl_handler(event):
    if IS_PAUSED:
        return await event.reply("⏳ **Bot abhi break le raha hai. Kripya 15-20 min baad try karein.**")
        
    user_id = event.sender_id
    if user_id in ongoing_downloads:
        return await event.reply("**❌ You already have an ongoing download. Please wait!**")
        
    if len(event.message.text.split()) < 2:
        return await event.reply("**Usage:** `/dl <video-link>`\n\nPlease provide a valid video link!")
        
    url = event.message.text.split()[1]
    TEMP_URLS[user_id] = url
    
    buttons = [
        [Button.inline("🎬 Download Video", data=b"smartdl_video"),
         Button.inline("🎧 Download Audio", data=b"smartdl_audio")]
    ]
    await event.reply("❓ **Aap is link se kya download karna chahte hain?**", buttons=buttons)

@client.on(events.CallbackQuery(pattern=b"smartdl_(video|audio)"))
async def smartdl_callback(event):
    user_id = event.sender_id
    if user_id not in TEMP_URLS:
        return await event.answer("❌ Link expired. Send /dl command again.", alert=True)
        
    url = TEMP_URLS.pop(user_id)
    choice = event.data.decode()
    await event.delete()
    
    ongoing_downloads[user_id] = True
    try:
        delay_time = random.uniform(2.5, 5.2)
        await asyncio.sleep(delay_time)
        
        platform = "insta" if "instagram.com" in url else "yt" if ("youtube.com" in url or "youtu.be" in url) else None
        
        if choice == "smartdl_audio":
            await process_audio(client, event, url, platform=platform)
        else:
            await process_video(client, event, url, platform=platform, check_duration_and_size=(platform=="yt"))
            
    except Exception as e:
        await event.respond(f"**Error:** `{e}`")
    finally:
        ongoing_downloads.pop(user_id, None)
 
user_progress = {}
 
def progress_callback(done, total, user_id):
    if user_id not in user_progress:
        user_progress[user_id] = {
            'previous_done': 0,
            'previous_time': time.time()
        }
    user_data = user_progress[user_id]
    percent = (done / total) * 100
    completed_blocks = int(percent // 10)
    remaining_blocks = 10 - completed_blocks
    progress_bar = "♦" * completed_blocks + "◇" * remaining_blocks
    done_mb = done / (1024 * 1024)   
    total_mb = total / (1024 * 1024)
    speed = done - user_data['previous_done']
    elapsed_time = time.time() - user_data['previous_time']
    if elapsed_time > 0:
        speed_bps = speed / elapsed_time   
        speed_mbps = (speed_bps * 8) / (1024 * 1024)   
    else:
        speed_mbps = 0
    if speed_bps > 0:
        remaining_time = (total - done) / speed_bps
    else:
        remaining_time = 0
    remaining_time_min = remaining_time / 60
    final = (
        f"╭──────────────────╮\n"
        f"│        **__Uploading...__** \n"
        f"├──────────\n"
        f"│ {progress_bar}\n\n"
        f"│ **__Progress:__** {percent:.2f}%\n"
        f"│ **__Done:__** {done_mb:.2f} MB / {total_mb:.2f} MB\n"
        f"│ **__Speed:__** {speed_mbps:.2f} Mbps\n"
        f"│ **__Time Remaining:__** {remaining_time_min:.2f} min\n"
        f"╰──────────────────╯\n\n"
        f"**__Powered by 🇮‌🇹‌'🇸‌ 🇭‌4️⃣🇷‌__**"
    )
    user_data['previous_done'] = done
    user_data['previous_time'] = time.time()
    return final
 
async def process_video(client, event, url, platform, check_duration_and_size=False):
    start_time = time.time()
    user_id = event.sender_id
    logger.info(f"Received link: {url}")
     
    cookies = None
    if platform:
        cookies = await get_user_cookie(user_id, platform)
        if not cookies:
            await event.reply(f"**❌ Aapne {platform.upper()} ki cookies add nahi ki hain.**\nPehle cookies.txt file bhejkar `/addcookie {platform}` reply karein.")
            return
 
    random_filename = get_random_string() + ".mp4"
    download_path = os.path.abspath(random_filename)
    logger.info(f"Generated random download path: {download_path}")
 
    temp_cookie_path = None
    if cookies:
        with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.txt') as temp_cookie_file:
            temp_cookie_file.write(cookies)
            temp_cookie_path = temp_cookie_file.name
        logger.info(f"Created temporary cookie file at: {temp_cookie_path}")
 
    thumbnail_file = None
    metadata = {'width': None, 'height': None, 'duration': None, 'thumbnail': None}
 
    ydl_opts = {
        'outtmpl': download_path,
        'format': 'best',
        'cookiefile': temp_cookie_path if temp_cookie_path else None,
        'writethumbnail': True,
        'verbose': True,
        'nocheckcertificate': True,
        'legacyserverconnect': True,
    }
    prog = None
    progress_message = await event.reply("**__Starting download...__**")
    logger.info("Starting the download process...")
    try:
        info_dict = await fetch_video_info(url, ydl_opts, progress_message, check_duration_and_size)
        if not info_dict:
            return
         
        await asyncio.to_thread(download_video, url, ydl_opts)
        title = info_dict.get('title', "Powered by 🇮‌🇹‌'🇸‌ 🇭‌4️⃣🇷‌")
        k = await get_video_metadata(download_path)      
        W = k['width']
        H = k['height']
        D = k['duration']
        metadata['width'] = info_dict.get('width') or W
        metadata['height'] = info_dict.get('height') or H
        metadata['duration'] = int(info_dict.get('duration') or 0) or D
        thumbnail_url = info_dict.get('thumbnail', None)
        THUMB = None
 
        if thumbnail_url:
            thumbnail_file = os.path.join(tempfile.gettempdir(), get_random_string() + ".jpg")
            await download_thumbnail_async(thumbnail_url, thumbnail_file)
            downloaded_thumb = thumbnail_file
            if downloaded_thumb:
                logger.info(f"Thumbnail saved at: {downloaded_thumb}")
 
        if thumbnail_file:
            THUMB = thumbnail_file
        else:
            THUMB = await screenshot(download_path, metadata['duration'], event.sender_id)

        chat_id = event.chat_id
        SIZE = 2 * 1024 * 1024
        caption = f"{title}"
     
        if os.path.exists(download_path) and os.path.getsize(download_path) > SIZE:
            prog = await client.send_message(chat_id, "**__Starting Upload...__**")
            await split_and_upload_file(app, chat_id, download_path, caption)
            await prog.delete()
         
        if os.path.exists(download_path):
            await progress_message.delete()
            prog = await client.send_message(chat_id, "**__Starting Upload...__**")
            uploaded = await fast_upload(
                client, download_path,
                reply=prog,
                progress_bar_function=lambda done, total: progress_callback(done, total, chat_id)
            )
            await client.send_file(
                event.chat_id,
                uploaded,
                caption=f"**{title}**",
                attributes=[
                    DocumentAttributeVideo(
                        duration=metadata['duration'],
                        w=metadata['width'],
                        h=metadata['height'],
                        supports_streaming=True
                    )
                ],
                thumb=THUMB if THUMB else None
            )
            if prog:
                await prog.delete()
        else:
            await event.reply(f"**❌ Server blocked the download (IP/SSL Error).**\n\n**🎥 Direct Link se dekhein:**\n{url}")
    except Exception as e:
        logger.exception("An error occurred during download or upload.")
        await event.reply(f"**❌ Video download fail ho gaya.**\n\n**🎥 Direct Link se dekhein:**\n{url}")
    finally:
        if os.path.exists(download_path):
            os.remove(download_path)
        if temp_cookie_path and os.path.exists(temp_cookie_path):
            os.remove(temp_cookie_path)
        if thumbnail_file and os.path.exists(thumbnail_file):
            os.remove(thumbnail_file)
 
async def split_and_upload_file(app, sender, file_path, caption):
    if not os.path.exists(file_path):
        await app.send_message(sender, "❌ File not found!")
        return

    file_size = os.path.getsize(file_path)
    start = await app.send_message(sender, f"ℹ️ File size: {file_size / (1024 * 1024):.2f} MB")
    PART_SIZE =  1.9 * 1024 * 1024 * 1024

    part_number = 0
    async with aiofiles.open(file_path, mode="rb") as f:
        while True:
            chunk = await f.read(PART_SIZE)
            if not chunk:
                break

            base_name, file_ext = os.path.splitext(file_path)
            part_file = f"{base_name}.part{str(part_number).zfill(3)}{file_ext}"

            async with aiofiles.open(part_file, mode="wb") as part_f:
                await part_f.write(chunk)

            edit = await app.send_message(sender, f"⬆️ Uploading part {part_number + 1}...")
            part_caption = f"{caption} \n\n**Part : {part_number + 1}**"
            await app.send_document(sender, document=part_file, caption=part_caption,
                progress=progress_bar,
                progress_args=("╭─────────────────────╮\n│      **🇮‌🇹‌'🇸‌ 🇭‌4️⃣🇷‌ Uploader**\n├─────────────────────", edit, time.time())
            )
            await edit.delete()
            os.remove(part_file)
            part_number += 1

    await start.delete()
    os.remove(file_path)

PROGRESS_BAR = """
│ **__Completed:__** {1}/{2}
│ **__Bytes:__** {0}%
│ **__Speed:__** {3}/s
│ **__ETA:__** {4}
╰─────────────────────╯
"""

async def get_seconds(time_string: str) -> int:
    def extract_value_and_unit(ts: str):
        value = ''.join(filter(str.isdigit, ts))
        unit = ts[len(value):].strip()
        return int(value) if value else 0, unit
    
    value, unit = extract_value_and_unit(time_string)
    time_units = {'s': 1, 'min': 60, 'hour': 3600, 'day': 86400, 'month': 86400 * 30, 'year': 86400 * 365}
    return value * time_units.get(unit, 0)

async def progress_bar(current: int, total: int, ud_type: str, message, start: float):
    now = time.time()
    diff = now - start
    
    if round(diff % 10) == 0 or current == total:
        percentage = (current * 100) / total
        speed = current / diff if diff else 0
        elapsed_time = round(diff * 1000)
        time_to_completion = round((total - current) / speed) * 1000 if speed else 0
        estimated_total_time = elapsed_time + time_to_completion

        elapsed_time_str = TimeFormatter(elapsed_time)
        estimated_total_time_str = TimeFormatter(estimated_total_time)

        progress = "".join(["♦" for _ in range(math.floor(percentage / 10))]) + \
                   "".join(["◇" for _ in range(10 - math.floor(percentage / 10))])
        
        progress_text = progress + PROGRESS_BAR.format(
            round(percentage, 2),
            humanbytes(current),
            humanbytes(total),
            humanbytes(speed),
            estimated_total_time_str if estimated_total_time_str else "0 s"
        )
        try:
            await message.edit(text=f"{ud_type}\n│ {progress_text}")
        except:
            pass

def humanbytes(size: int) -> str:
    if not size: return ""
    power = 2**10
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    n = 0
    while size > power and n < len(units) - 1:
        size /= power
        n += 1
    return f"{round(size, 2)} {units[n]}"

def TimeFormatter(milliseconds: int) -> str:
    seconds, milliseconds = divmod(milliseconds, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    parts = []
    if days: parts.append(f"{days}d")
    if hours: parts.append(f"{hours}h")
    if minutes: parts.append(f"{minutes}m")
    if seconds: parts.append(f"{seconds}s")
    if milliseconds: parts.append(f"{milliseconds}ms")
    return ', '.join(parts)

def convert(seconds: int) -> str:
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}:{minutes:02d}:{seconds:02d}"

@client.on(events.CallbackQuery(pattern=b"^run_dl$"))
async def direct_dl(event):
    await event.delete()
    await event.respond("💀 **Smart Downloader**\n\nKripya apna link is format me bhejen:\n👉 `/dl <link>`")