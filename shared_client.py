from telethon import TelegramClient
from telethon.sessions import MemorySession
from config import API_ID, API_HASH, BOT_TOKEN, STRING
from pyrogram import Client
import pyromod # Ye Pyrogram ko conversational bana dega
import sys

import random

# 🟢 HACK 1: PYROGRAM CONNECTION OVERRIDE FOR 4-10MB/s SPEED
import pyrogram
pyrogram.utils.MIN_CHUNK_SIZE = 65536 * 16  # Approx 1MB chunks ki request bhejega
pyrogram.utils.MAX_WORKERS = 16  # 16 Parallel connections allow karega

if hasattr(pyrogram.utils, 'MAX_CONCURRENT_TRANSMISSIONS'):
    pyrogram.utils.MAX_CONCURRENT_TRANSMISSIONS = 10

client = TelegramClient("telethon_bot_session", API_ID, API_HASH)

# 🟢 FAST MODE: max_concurrent_transmissions ko 1 se badhakar 10 kar diya gaya hai
app = Client(
    "pyrogrambot", 
    api_id=API_ID, 
    api_hash=API_HASH, 
    bot_token=BOT_TOKEN,
    max_concurrent_transmissions=10  
)


# RANDOM DEVICE SPOOFING DATA
DEVICES = ["Samsung Galaxy S24 Ultra", "Google Pixel 8 Pro", "OnePlus 12", "Xiaomi 14 Pro", "Vivo X100 Pro", "iPhone 15 Pro Max", "Poco F5"]
OS_VERSIONS = ["Android 14", "Android 13", "Android 12", "iOS 17.2", "iOS 16.5"]
APP_VERSIONS = ["10.14.0", "10.13.1", "10.12.0", "10.11.1", "10.15.0"]

#   ANTI-BAN SECURITY: Dynamic Random Device Spoofing
# 🟢 FAST MODE: Userbot ki speed block bhi 1 se hatakar 10 kar di gayi hai
userbot = Client(
    "4gbbot", 
    api_id=API_ID, 
    device_model=random.choice(DEVICES),
    system_version=random.choice(OS_VERSIONS),
    app_version=random.choice(APP_VERSIONS),
    max_concurrent_transmissions=10, 
    sleep_threshold=120
) if STRING else None

async def start_client():
    if not client.is_connected():
        await client.start(bot_token=BOT_TOKEN)
        print("SpyLib (Telethon) started in Memory Mode...")
    
    if STRING and userbot:
        try:
            await userbot.start()
            print("Userbot started cleanly...")
        except Exception as e:
            print(f"Hey honey!! check your premium string session, it may be invalid or expired: {e}")
            sys.exit(1)
            
    await app.start()
    print("Pyro App Started cleanly...")
    return client, app, userbot