import concurrent.futures
import time
import os
import uuid
import re
import asyncio
import logging
from datetime import datetime, timedelta
import yt_dlp
from motor.motor_asyncio import AsyncIOMotorClient
from groq import AsyncGroq

from config import MONGO_DB as MONGO_URI, DB_NAME

# 🟢 Pillow Library for Advanced Thumbnail Font Watermarking
try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    Image, ImageDraw, ImageFont = None, None, None
    print("⚠️ Pillow not installed! Run 'pip install Pillow'")

try:
    from theme_config import FONT_DIR
except ImportError:
    FONT_DIR = "fonts"

# GLOBAL VARIABLE FOR HUMAN SLEEP CYCLE
IS_PAUSED = False
PROCESS_SEMAPHORE = asyncio.Semaphore(3)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

PUBLIC_LINK_PATTERN = re.compile(r'(https?://)?(t\.me|telegram\.me)/([^/]+)(/(\d+))?')
PRIVATE_LINK_PATTERN = re.compile(r'(https?://)?(t\.me|telegram\.me)/c/(\d+)(/(\d+))?')
VIDEO_EXTENSIONS = {"mp4", "mkv", "avi", "mov", "wmv", "flv", "webm", "mpeg", "mpg", "3gp"}

# Connection pooling jisse bot DB ko baar-baar open/close na kare
mongo_client = AsyncIOMotorClient(MONGO_URI, maxPoolSize=50, minPoolSize=10)
db = mongo_client[DB_NAME]
users_collection = db["users"]
premium_users_collection = db["premium_users"]
statistics_collection = db["statistics"]
codedb = db["redeem_code"]
admin_auth_collection = db["admin_auth"]
admin_logs_collection = db["admin_logs"]

# ------- < start > Session Encoder don't change -------

# System Core Variables (Dnt Touch)
a1 = "SDRSX1NSQ19ib3Q="
a2 = "Mw=="
a3 = "Z2V0X21lc3NhZ2Vz"
a4 = "cmVwbHlfcGhvdG8="
a5 = "c3RhcnQ="
attr1 = "cGhvdG8="
attr2 = "ZmlsZV9pZA=="

# 🌟 PREMIUM SAAS WELCOME MESSAGE & LINKS (Encrypted with Emojis) 🌟
a7 = "8J+MnyAqKldlbGNvbWUgdG8gSDRSIFNSQyBQcm8sIHt1c2VyX25hbWV9ISoqIPCfjJ8KCkFhcGthIFVsdGltYXRlICoqQ29udGVudCBNYW5hZ2VtZW50ICYgVGVsZWdyYW0gQXV0b21hdGlvbiBXb3Jrc3BhY2UqKi4gSHVtIHJlc3RyaWN0ZWQgbWVkaWEgZG93bmxvYWRpbmcga28gZWsgbmV4dC1sZXZlbCBleHBlcmllbmNlIGJhbmF0ZSBoYWluLgoK4pyoICoqRXhjbHVzaXZlIEZlYXR1cmVzIEluY2x1ZGVkOioqCvCfk6UgKipTZWFtbGVzcyBFeHRyYWN0aW9uOioqIEJ5cGFzcyByZXN0cmljdGVkIGNoYW5uZWxzICYgZG93bmxvYWQgZnJvbSBZVC9JbnN0YS4K8J+kliAqKkFJLVBvd2VyZWQgUmVuYW1pbmc6KiogU21hcnQgY2FwdGlvbnMgJiBmaWxlIG5hbWVzIGhhbmRsZWQgYnkgQUkuCvCflIQgKipBdXRvU3luYyAyLjA6KiogWmVyby1kb3dudGltZSBiYWNrZ3JvdW5kIGNoYW5uZWwgbWlycm9yaW5nLgrwn46oICoqQ3VzdG9tIEJyYW5kaW5nOioqIEFkZCB5b3VyIG93biB3YXRlcm1hcmtzIHRvIFBERnMgJiB2aWRlb3MgYXV0b21hdGljYWxseS4K8J+agCAqKkh5cGVyLVNwZWVkIEJhdGNoOioqIEV4dHJhY3QgdGhvdXNhbmRzIG9mIGZpbGVzIHdpdGhvdXQgc2VydmVyIGNyYXNoZXMuCgrwn46BICoqRWFybiBGcmVlIFZJUCBBY2Nlc3MhKioKVXNlIGAvcmVmZXJgIHRvIGludml0ZSB1c2VycyBhbmQgdW5sb2NrIHByZW1pdW0gZmVhdHVyZXMgZm9yIGZyZWUuCgrwn5GHIF9FeHBsb3JlIHRoZSBkYXNoYm9hcmQgYmVsb3cgdG8gZ2V0IHN0YXJ0ZWQ6Xw=="
a8 = "8J+Rq+KAjeKAniBDb250YWN0IERldmVsb3Blcg=="
a9 = "8J+ToiBVcGRhdGVzIENoYW5uZWw="
a10 = "aHR0cHM6Ly90Lm1lL0g0Ul9Db250YWN0X2JvdA=="
a11 = "aHR0cHM6Ly90Lm1lL0g0Ul9TcmNfcm9ib3Q="
refer_enc = "8J+OiCAqKldhbnQgRnJlZSBQcmVtaXVtPyoqClVzZSAvcmVmZXIgY29tbWFuZCB0byBpbnZpdGUgZnJpZW5kcyBhbmQgZ2V0IGEgMS1EYXkgVklQIHBsYW4gY29tcGxldGVseSBGUkVFIQ=="

# ------- < end > Session Encoder don't change --------

# 🟢 CAPTION BEAUTIFIER
def beautify_caption(text):
    if not text: return ""
    
    # Existing emojis ko clean karo taaki output me duplicate na ho
    text = re.sub(r'[🎬📁🏷️👤🖥️📦🔢]', '', text)
    
    # Topic string standardization yahan bhi apply hogi
    text = re.sub(r'(?i)Number Of Digits', 'No. of Digit', text)
    
    replacements = {
        r"(?i)Index\s*:": "\n🔢 **Index:**",
        r"(?i)Title\s*:": "\n🎬 **Title:**",
        r"(?i)Topic\s*:": "\n📁 **Topic:**",
        r"(?i)Batch\s*:": "\n🏷️ **Batch:**",
        r"(?i)Extracted By\s*:": "\n👤 **Extracted By:**",
        r"(?i)Quality\s*:": "\n🖥️ **Quality:**",
        r"(?i)Size\s*:": "\n📦 **Size:**"
    }
    for pattern, new_text in replacements.items(): 
        text = re.sub(pattern, new_text, text)
        
    text = re.sub(r'\n{3,}', '\n\n', text).strip()
    return f"━━━━━━━━━━━━━━━━━━━\n{text}\n━━━━━━━━━━━━━━━━━━━" if text else ""

# 🟢 CUSTOM THUMBNAIL WATERMARKING (TEXT VIA PILLOW)
async def generate_thumbnail(video_path, watermark, user_id):
    if not video_path or not os.path.exists(video_path): 
        return None
    ext = video_path.lower().split('.')[-1]
    if ext not in ['mp4', 'mkv', 'avi', 'mov', 'webm']: 
        return None
    thumb_path = f"{video_path}_thumb.jpg"
    
    cmd = ["ffmpeg", "-i", video_path, "-ss", "00:00:01", "-vframes", "1", "-y", thumb_path, "-loglevel", "quiet"]
    try:
        proc = await asyncio.create_subprocess_exec(*cmd)
        await proc.wait()
    except Exception as e:
        print(f"Thumb extraction error: {e}")
        return None

    if not os.path.exists(thumb_path):
        return None

    if watermark and watermark.lower() != "skip" and Image:
        font_file = await get_user_data_key(user_id, "thumb_font", "default.ttf")
        font_color = await get_user_data_key(user_id, "thumb_color", "white")
        
        try:
            def apply_pil_watermark():
                img = Image.open(thumb_path).convert("RGBA")
                draw = ImageDraw.Draw(img)
                try:
                    font_size = int(img.width / 12)
                    actual_font_path = os.path.join(FONT_DIR, font_file)
                    font = ImageFont.truetype(actual_font_path, font_size)
                except IOError:
                    font = ImageFont.load_default()
                
                bbox = draw.textbbox((0, 0), watermark, font=font)
                w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
                x, y = (img.width - w) / 2, (img.height - h) / 2
                
                pad = int(img.width/50)
                draw.rectangle([x-pad, y-pad, x+w+pad, y+h+pad], fill=(0,0,0,71))
                
                shadow_color = "black" if font_color != "black" else "white"
                for dx in [-2, 0, 2]:
                    for dy in [-2, 0, 2]:
                        draw.text((x+dx, y+dy), watermark, font=font, fill=shadow_color)
                        
                draw.text((x, y), watermark, font=font, fill=font_color)
                img.convert('RGB').save(thumb_path, "JPEG", quality=95)

            await asyncio.to_thread(apply_pil_watermark)
        except Exception as e:
            print(f"Pillow Watermarking Error: {e}")
            
    return thumb_path

def is_private_link(link):
    return bool(PRIVATE_LINK_PATTERN.match(link))

def thumbnail(sender):
    return f'{sender}.jpg' if os.path.exists(f'{sender}.jpg') else None

def hhmmss(seconds):
    return time.strftime('%H:%M:%S', time.gmtime(seconds))

def E(L):   
    private_match = re.match(r'https://t\.me/c/(\d+)/(?:\d+/)?(\d+)', L)
    public_match = re.match(r'https://t\.me/([^/]+)/(?:\d+/)?(\d+)', L)
    
    if private_match:
        return f'-100{private_match.group(1)}', int(private_match.group(2)), 'private'
    elif public_match:
        return public_match.group(1), int(public_match.group(2)), 'public'
    
    return None, None, None

def get_display_name(user):
    if user.first_name and user.last_name:
        return f"{user.first_name} {user.last_name}"
    elif user.first_name:
        return user.first_name
    elif user.last_name:
        return user.last_name
    elif user.username:
        return user.username
    else:
        return "Unknown User"

def sanitize_filename(filename):
    return re.sub(r'[<>:"/\\|?*]', '_', filename)

def get_dummy_filename(info):
    file_type = info.get("type", "file")
    extension = {
        "video": "mp4",
        "photo": "jpg",
        "document": "pdf",
        "audio": "mp3"
    }.get(file_type, "bin")
    
    return f"downloaded_file_{int(time.time())}.{extension}"

async def is_private_chat(event):
    return event.is_private

async def save_user_data(user_id, key, value):
    await users_collection.update_one(
        {"user_id": user_id},
        {"$set": {key: value}},
        upsert=True
    )

async def download_youtube_video(url, uid):
    async with PROCESS_SEMAPHORE:
        from utils.db import get_user_cookie
        cookie_file = f"yt_cookies_{uid}.txt"
        
        cookies = await get_user_cookie(uid, "yt")
                
        if cookies:
            with open(cookie_file, "w", encoding="utf-8") as f:
                f.write(cookies)
                
        try:
            def _dl():
                ydl_opts = {
                    'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                    'merge_output_format': 'mp4',
                    'outtmpl': f'yt_download_{uid}_%(id)s.%(ext)s',
                    'quiet': True,
                    'no_warnings': True,
                    'nocheckcertificate': True, 
                    'legacyserverconnect': True 
                }
                if os.path.exists(cookie_file):
                    ydl_opts['cookiefile'] = cookie_file
                    
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    filename = ydl.prepare_filename(info)
                    base, _ = os.path.splitext(filename)
                    for ext in ['.mp4', '.mkv', '.webm']:
                        if os.path.exists(base + ext):
                            return base + ext
                    return filename
                    
            file_path = await asyncio.to_thread(_dl)
            return file_path
            
        except Exception as e:
            logger.error(f"❌ YouTube Download Error: {e}")
            return None
        finally:
            if os.path.exists(cookie_file):
                try: os.remove(cookie_file)
                except: pass

async def copy_header_and_repair(corrupt_file, reference_file):
    if not os.path.exists(corrupt_file) or not os.path.exists(reference_file):
        return None
        
    logger.info(f"🛠 Starting Ultimate Repair for: {corrupt_file}")
    
    untrunc_out = f"{corrupt_file}_fixed.mp4" 
    final_out = f"final_repaired_{time.time()}.mp4"

    try:
        logger.info("🔄 Phase 1: Running Untrunc to rebuild headers...")
        proc1 = await asyncio.create_subprocess_exec(
            "untrunc", reference_file, corrupt_file,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        await asyncio.wait_for(proc1.wait(), timeout=120)

        if not os.path.exists(untrunc_out) or os.path.getsize(untrunc_out) < 1024:
            logger.error("❌ Untrunc failed to generate a valid file.")
            return None

        logger.info("🔄 Phase 2: Remuxing with FFMPEG to align timestamps...")
        proc2 = await asyncio.create_subprocess_exec(
            "ffmpeg", 
            "-err_detect", "ignore_err", 
            "-i", untrunc_out,
            "-c", "copy",                
            "-map", "0",
            "-movflags", "faststart",    
            "-y", final_out,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        await asyncio.wait_for(proc2.wait(), timeout=120)

        if os.path.exists(final_out) and os.path.getsize(final_out) > 1024:
            os.remove(corrupt_file)
            if os.path.exists(untrunc_out): os.remove(untrunc_out)
            os.rename(final_out, corrupt_file)
            logger.info("✅ Ultimate Repair Successful!")
            return corrupt_file
            
        elif os.path.exists(untrunc_out) and os.path.getsize(untrunc_out) > 1024:
            os.remove(corrupt_file)
            os.rename(untrunc_out, corrupt_file)
            logger.info("✅ Repair Successful (Untrunc Phase 1 only)!")
            return corrupt_file

        return None

    except Exception as e:
        logger.error(f"❌ Repair Process Error: {e}")
        return None
        
    finally:
        for temp_f in [untrunc_out, final_out]:
            if os.path.exists(temp_f) and temp_f != corrupt_file:
                try: os.remove(temp_f)
                except: pass

async def get_user_data_key(user_id, key, default=None):
    user_data = await users_collection.find_one({"user_id": int(user_id)})
    return user_data.get(key, default) if user_data else default

async def get_user_data(user_id):
    try:
        user_data = await users_collection.find_one({"user_id": user_id})
        return user_data
    except Exception as e:
        return None

async def save_user_session(user_id, session_string):
    try:
        await users_collection.update_one(
            {"user_id": user_id},
            {"$set": {
                "session_string": session_string,
                "updated_at": datetime.now()
            }},
            upsert=True
        )
        logger.info(f"Saved session for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error saving session for user {user_id}: {e}")
        return False

async def get_or_create_fingerprint(user_id):
    """🔥 ANTI-BAN: User ko hamesha ek hi 'Virtual Phone' dega taaki account ban na ho"""
    import random
    
    # Check karo agar user ka phone pehle se save hai
    user_data = await users_collection.find_one({"user_id": int(user_id)})
    
    if user_data and "device_fingerprint" in user_data:
        return user_data["device_fingerprint"]
        
    # Agar naya session hai toh ek premium device lock kar do
    dev_models = ["Samsung Galaxy S23 Ultra", "Google Pixel 7 Pro", "OnePlus 11R", "Xiaomi 13 Pro", "Vivo X90", "Realme GT 2 Pro", "Asus ROG Phone 7"]
    sys_versions = ["Android 14", "Android 13", "Android 12", "Android 11"]
    app_versions = ["10.14.0", "10.13.2", "10.12.5", "10.11.0", "10.10.1"]
    
    new_fingerprint = {
        "device_model": random.choice(dev_models),
        "system_version": random.choice(sys_versions),
        "app_version": random.choice(app_versions),
        "lang_code": "en"
    }
    
    # Naye phone ko database me hamesha ke liye SAVE kar do
    await users_collection.update_one(
        {"user_id": int(user_id)},
        {"$set": {"device_fingerprint": new_fingerprint}},
        upsert=True
    )
    
    return new_fingerprint

async def remove_user_session(user_id):
    try:
        await users_collection.update_one(
            {"user_id": user_id},
            {"$unset": {"session_string": ""}}
        )
        logger.info(f"Removed session for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error removing session for user {user_id}: {e}")
        return False

async def save_user_bot(user_id, bot_token):
    try:
        await users_collection.update_one(
            {"user_id": user_id},
            {"$set": {
                "bot_token": bot_token,
                "updated_at": datetime.now()
            }},
            upsert=True
        )
        logger.info(f"Saved bot token for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error saving bot token for user {user_id}: {e}")
        return False

async def remove_user_bot(user_id):
    try:
        await users_collection.update_one(
            {"user_id": user_id},
            {"$unset": {"bot_token": ""}}
        )
        logger.info(f"Removed bot token for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error removing bot token for user {user_id}: {e}")
        return False

async def process_text_with_rules(user_id, text):
    if not text:
        return ""
    
    try:
        replacements = await get_user_data_key(user_id, "replacement_words", {})
        delete_words = await get_user_data_key(user_id, "delete_words", [])
        
        processed_text = text
        for word, replacement in replacements.items():
            processed_text = re.sub(re.escape(word), replacement, processed_text, flags=re.IGNORECASE)
        
        if delete_words:
            for word in delete_words:
                processed_text = re.sub(re.escape(word), "", processed_text, flags=re.IGNORECASE)
            
        # Sirf extra spaces hatayega, enter (\n) nahi
        processed_text = re.sub(r'[ \t]{2,}', ' ', processed_text)
        processed_text = processed_text.strip()
        
        return processed_text
    except Exception as e:
        logger.error(f"Error processing text with rules: {e}")
        return text

async def screenshot(video: str, duration: int, sender: str) -> str | None:
    existing_screenshot = f"{sender}.jpg"
    if os.path.exists(existing_screenshot):
        return existing_screenshot

    time_stamp = hhmmss(duration // 2)
    output_file = datetime.now().isoformat("_", "seconds") + ".jpg"

    cmd = [
        "ffmpeg",
        "-ss", time_stamp,
        "-i", video,
        "-frames:v", "1",
        output_file,
        "-y"
    ]

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    stdout, stderr = await process.communicate()

    if os.path.isfile(output_file):
        return output_file
    else:
        print(f"FFmpeg Error: {stderr.decode().strip()}")
        return None

async def get_video_metadata(file_path):
    default_values = {'width': 1, 'height': 1, 'duration': 1}
    try:
        # FIX: Replaced heavy OpenCV with lightweight ffprobe for 10x faster processing
        cmd = [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height,duration",
            "-of", "csv=p=0:s=x", file_path
        ]
        
        proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, _ = await proc.communicate()
        
        output = stdout.decode().strip()
        if output:
            parts = output.split('x')
            if len(parts) >= 3:
                width = int(parts[0])
                height = int(parts[1])
                try:
                    duration = int(float(parts[2]))
                except ValueError:
                    duration = 1
                return {'width': width, 'height': height, 'duration': duration}
                
        return default_values
    except Exception as e:
        logger.error(f"Error in get_video_metadata via ffprobe: {e}")
        return default_values

async def add_premium_user(user_id, duration_value, duration_unit):
    try:
        now = datetime.now()
        expiry_date = None
        
        if duration_unit == "min":
            expiry_date = now + timedelta(minutes=duration_value)
        elif duration_unit == "hours":
            expiry_date = now + timedelta(hours=duration_value)
        elif duration_unit == "days":
            expiry_date = now + timedelta(days=duration_value)
        elif duration_unit == "weeks":
            expiry_date = now + timedelta(weeks=duration_value)
        elif duration_unit == "month":
            expiry_date = now + timedelta(days=30 * duration_value)
        elif duration_unit == "year":
            expiry_date = now + timedelta(days=365 * duration_value)
        elif duration_unit == "decades":
            expiry_date = now + timedelta(days=3650 * duration_value)
        else:
            return False, "Invalid duration unit"
            
        await premium_users_collection.update_one(
            {"user_id": user_id},
            {"$set": {
                "user_id": user_id,
                "subscription_start": now,
                "subscription_end": expiry_date,
                "expireAt": expiry_date
            }},
            upsert=True
        )
        
        return True, expiry_date
    except Exception as e:
        logger.error(f"Error adding premium user {user_id}: {e}")
        return False, str(e)

async def is_premium_user(user_id):
    try:
        user = await premium_users_collection.find_one({"user_id": user_id})
        if user and "subscription_end" in user:
            now = datetime.now()
            return now < user["subscription_end"]
        return False
    except Exception as e:
        logger.error(f"Error checking premium status for {user_id}: {e}")
        return False

async def get_premium_details(user_id):
    try:
        user = await premium_users_collection.find_one({"user_id": user_id})
        if user and "subscription_end" in user:
            return user
        return None
    except Exception as e:
        logger.error(f"Error getting premium details for {user_id}: {e}")
        return None

async def log_admin_activity(admin_id, admin_name, action, target="N/A"):
    """Admin ki har activity ko database me save karega"""
    try:
        await admin_logs_collection.insert_one({
            "admin_id": admin_id,
            "admin_name": admin_name,
            "action": action,
            "target": target,
            "timestamp": datetime.now()
        })
    except Exception as e:
        logger.error(f"Activity log error: {e}")

# 🟢 THE AI MULTI-KEY ROTATION ENGINE
async def ai_rewrite_caption(original_caption, file_name="", custom_name="🇮‌🇹‌'🇸‌ 🇭‌4⃣🇷‌", custom_template=None):
    logger = logging.getLogger(__name__)
    
    # 🟢 1. BULLETPROOF KEY EXTRACTOR
    # Chahe naye secret me ho ya purane me, dono ko uthao aur merge kar do
    raw_keys_1 = os.environ.get("GROQ_API_KEYS", "")
    raw_keys_2 = os.environ.get("GROQ_API_KEY", "")
    
    combined_raw_keys = f"{raw_keys_1},{raw_keys_2}"
    
    # Ab isko comma se tod do aur extra spaces/kachra hata do
    keys_to_try = []
    for k in combined_raw_keys.split(","):
        cleaned_key = k.strip()
        # Sirf valid dikhne wali keys (lambai > 20) ko hi list me daalo
        if cleaned_key and len(cleaned_key) > 20:
            keys_to_try.append(cleaned_key)

    # Agar bot ke paas koi key nahi hai toh original text bhej do
    if not keys_to_try:
        return original_caption if original_caption else file_name

    # 🟢 2. Tumhara Prompt & Context Logic
    context_hint = f"File Name: {file_name}" if file_name else ""
    text_to_rewrite = original_caption if original_caption and original_caption.strip() else "No caption provided. Use File Name."
    
    if custom_template:
        format_instructions = f"""
        The user has provided a CUSTOM TEMPLATE design. Use exactly this structure. 
        Extract the required details and fill them in. DO NOT copy text blindly.
        
        CUSTOM TEMPLATE REFERENCE:
        {custom_template}
        """
    else:
        format_instructions = f"""
        FORMATTING TEMPLATE:
        ━━━━━━━━━━━━━━━━━━━
        ——— ✦ [ID] ✦ ———
        [Media Type Line]
         
         🎞 𝐿𝑒𝑐𝑡𝑢𝑟𝑒 : [Specific Sub-Topic/Lecture Details]
         
         📝 𝑇𝑜𝑝𝑖𝑐 : [Topic Name]
         
         🔖 𝐶ℎ𝑎𝑝𝑡𝑒𝑟 : [Chapter Name]
         
         📖 𝑆𝑢𝑏𝑗𝑒𝑐𝑡 : [Subject Name]
         
         📚 𝐵𝑎𝑡𝑐ℎ : [Batch Name]
         
         🌟 𝐸𝑥𝑡𝑟𝑎𝑐𝑡𝑒𝑑 𝐵𝑦 : {custom_name}
        ━━━━━━━━━━━━━━━━━━━
        """

    prompt = f"""
    You are an elite, highly intelligent Data Parser for a Premium Educational Telegram Channel.
    Your output MUST be beautiful, clean, and strictly avoid redundancy.

    CRITICAL EXTRACTION RULES:
    1. AVOID REDUNDANCY (MOST IMPORTANT RULE): 
       - DO NOT repeat the same concept in Chapter, Topic, and Lecture.
       - Example Raw Data: Title "HCF AND LCM MISCELLANEOUS QUESTIONS CLASS 9", Topic "MATHEMATICS - HCF & LCM"
       - BAD OUTPUT: Chapter = HCF AND LCM, Topic = HCF & LCM, Lecture = HCF AND LCM MISCELLANEOUS
       - GOOD OUTPUT: Subject = MATHEMATICS, Chapter = HCF & LCM, Topic = Miscellaneous Questions Class 9.
       - Action: Remove the Chapter name from the Lecture/Topic if it's already mentioned. Extract only the distinct sub-topic.
    2. CLEAN TITLE CASING: Format long uppercase strings into Title Case for better readability. E.g., "MISCELLANEOUS QUESTIONS CLASS 9" should become "Miscellaneous Questions Class 9".
    3. JUNK REMOVAL: Strip exact dates (e.g., 2024-04-13), usernames (e.g., ImTgArtist, ImTgRowoon), and random IDs from the names.
    4. MEDIA TYPE AWARENESS: 
       - Video: 🆔 𝑉𝑖𝑑𝑒𝑜 𝑰𝑑 : [ID]
       - PDF: 📑 𝑃𝐷𝐹 𝑰𝑑 : [ID]
       - If the file is a PDF or Image, COMPLETELY DELETE the '🎞 𝐿𝑒𝑐𝑡𝑢𝑟𝑒' line.
    5. OMIT MISSING/REDUNDANT DATA: If a distinct Topic or Lecture cannot be found without repeating the Chapter, DELETE that line entirely. Do not write "N/A" or "None".

    {format_instructions}
    
    Context Data:
    {context_hint}
    Original Context/Caption: 
    {text_to_rewrite}
    
    Output ONLY the finalized template. No extra words, no explanations.
    """
    
    # 🔄 3. MULTI-API KEY ROTATION ENGINE
    for index, current_key in enumerate(keys_to_try):
        try:
            from groq import AsyncGroq
            client = AsyncGroq(api_key=current_key)
            
            chat_completion = await client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.1-8b-instant", 
                temperature=0.1, 
                timeout=25
            )
            
            final_text = chat_completion.choices[0].message.content.strip()
            
            # 🟢 4. Tumhara Python Safety Net
            if final_text:
                clean_lines = []
                for line in final_text.split('\n'):
                    if not re.search(r'\b(N/A|None|null)\b', line, re.IGNORECASE):
                        if "📑 𝑃𝐷𝐹" in final_text and "🎞 𝐿𝑒𝑐𝑡𝑢𝑟𝑒" in line: continue
                        if "🖼️ 𝐼𝑀𝐺" in final_text and "🎞 𝐿𝑒𝑐𝑡𝑢𝑟𝑒" in line: continue
                        clean_lines.append(line)
                
                final_text = "\n".join(clean_lines)
                final_text = re.sub(r'\n{3,}', '\n\n', final_text)
                
                if len(final_text) > 10:
                    return final_text
                    
        except Exception as e:
            error_str = str(e).lower()
            if "401" in error_str or "invalid_api_key" in error_str:
                logger.warning(f"⚠️ Groq API Key {index + 1}/{len(keys_to_try)} Invalid. Switching to next key...")
                continue # Key galat hai? Agli try karo
            elif "429" in error_str or "rate_limit" in error_str:
                logger.warning(f"⚠️ Groq API Key {index + 1}/{len(keys_to_try)} Limit Exceeded. Switching to next key...")
                continue # Limit khatam? Agli key try karo!
            else:
                logger.warning(f"⚠️ Groq API Attempt failed on Key {index + 1}: {e}")
                await asyncio.sleep(2)
                continue # Dusra error aaya? Agli key try karo!
                
    # 🛑 5. AGAR SAARI KEYS FAIL HO GAYI!
    logger.error("❌ ALL GROQ API KEYS FAILED! Falling back to original caption.")
    return original_caption if original_caption else file_name


async def auto_delete_message(message, delay=300):
    """Global Ghost Mode: Message ko 5 min baad delete karega bina bot ko roke"""
    try:
        await asyncio.sleep(delay)
        await message.delete()
    except Exception:
        pass
