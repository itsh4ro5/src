import asyncio
import uvloop

# 1. uvloop policy set karo
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

# 🔥 FIX: Naya loop create karke OS thread me set karo BEFORE any Pyrogram imports
try:
    loop = asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
import os
import sys
import random
import shutil
import time
import importlib
import logging
import traceback
from datetime import datetime
from utils.func import premium_users_collection
from pyrogram.types import BotCommand  
from pyrogram import idle

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[logging.StreamHandler()] 
)
logger = logging.getLogger(__name__)

# 🟢 SPEED BOOST: Activate Ultra-Fast Async Engine
import uvloop
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
logger.info("⚡ uvloop forcefully activated for maximum download speeds.")

from shared_client import start_client, app
import utils.func as global_state

async def setup_bot_commands():
    try:
        await app.set_bot_commands([
            BotCommand("start", "🆓 Start the bot & check status"),
            BotCommand("help", "🆓 View all commands & features"),
            BotCommand("login", "🆓 Login to save private restricted content"),
            BotCommand("logout", "🆓 Logout from your current session"),
            BotCommand("single", "🆓 Extract a single restricted message"),
            BotCommand("batch", "🌟 Extract multiple restricted messages"),
            BotCommand("forward", "🆓 Toggle Fast Forward Mode (No Download)"),
            BotCommand("settings", "🆓 🎨 Settings & Customize Thumbnail"),
            BotCommand("id", "🆓 🆔 Get Chat/User ID"),
            BotCommand("cancel", "🆓 Cancel the currently active task"),
            BotCommand("redeem", "🆓 Redeem your Premium Code"),
            BotCommand("setbot", "🌟 Set your custom bot token"),
            BotCommand("rembot", "🌟 Remove your custom bot token"),
        ])
        logger.info("✅ Advanced Bot command menu set successfully!")
    except Exception as e:
        logger.error(f"⚠️ Failed to set bot commands: {e}")

# --- 🟢 SMART VPS CLEANUP ROUTINE ---
async def auto_cleanup_routine():
    """Har 30 min me kachra saaf karega (Non-blocking mode)"""
    DOWNLOAD_DIR = "downloads"
    # Ensure folder exists
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    
    while True:
        try:
            logger.info("🧹 Starting VPS Auto-Cleanup routine...")
            current_time = time.time()
            deleted_files = 0
            freed_space = 0
            
            # Blocking code ko thread me run karo
            def cleanup_files():
                nonlocal deleted_files, freed_space
                for filename in os.listdir(DOWNLOAD_DIR):
                    file_path = os.path.join(DOWNLOAD_DIR, filename)
                    if os.path.isfile(file_path) and (current_time - os.path.getmtime(file_path)) > 7200:
                        size = os.path.getsize(file_path)
                        os.remove(file_path)
                        deleted_files += 1
                        freed_space += size

            await asyncio.to_thread(cleanup_files) # Async way to run blocking I/O
                        
            if deleted_files > 0:
                freed_mb = freed_space / (1024 * 1024)
                logger.info(f"Aggressive Cleanup Done: Deleted {deleted_files} files. Freed {freed_mb:.2f} MB.")
                        
        except Exception as e:
            logger.error(f"Cleanup Error: {e}")
            
        await asyncio.sleep(1800)
# ------------------------------------

# --- 🟢 PREMIUM AUTO-DEMOTION & ALERT ROUTINE ---
async def premium_expiry_routine():
    """Har 1 ghante me check karega ki kiska plan expire hua hai aur alert bhejega"""
    while True:
        try:
            now = datetime.now()
            # Un users ko dhoondo jinka expiry time aaj se pehle ka ho chuka hai
            expired_users = premium_users_collection.find({"subscription_end": {"$lt": now}})
            
            async for user in expired_users:
                user_id = user.get("user_id")
                if user_id:
                    try:
                        # User ko alert bhejna
                        await app.send_message(
                            user_id, 
                            "⚠️ **Notice:** Your Premium Subscription has expired! You have been downgraded to the Free plan. Contact the owner to renew."
                        )
                    except Exception as e:
                        # Agar user ne bot block kar diya ho
                        logger.warning(f"Failed to send expiry alert to {user_id}: {e}")
                    
                    # Database se officially delete karna
                    await premium_users_collection.delete_one({"user_id": user_id})
                    logger.info(f"⬇️ Demoted user {user_id} to Free plan due to expiry.")
                    
        except Exception as e:
            logger.error(f"❌ Premium Expiry Routine Error: {e}")
            
        # Agli checking 1 ghante (3600 seconds) baad hogi
        await asyncio.sleep(3600)
# ------------------------------------------------

async def load_and_run_plugins():
    plugin_dir = "plugins"
    plugins = [f[:-3] for f in os.listdir(plugin_dir) if f.endswith(".py") and f != "__init__.py"]

    for plugin in plugins:
        try:
            importlib.import_module(f"plugins.{plugin}")
            print(f"✅ Loaded plugin: {plugin}")
        except Exception as e:
            logger.error(f"❌ ERROR loading plugin '{plugin}':", exc_info=True)

async def main():
    await start_client()  # Pehle client start karo
    await load_and_run_plugins() # Fir plugins load karo
    await setup_bot_commands()  
    
    # 🟢 Start the Background Tasks
    asyncio.create_task(auto_cleanup_routine())
    asyncio.create_task(premium_expiry_routine()) # <-- YE NAYI LINE ADD KI HAI
    
    logger.info("🚀 Bot is Online and Ready to take commands!")
    await idle()  # Ye bot ko active rakhega saari commands receive karne ke liye

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    print("Starting clients ...")
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("Shutting down...")
    except (Exception, SystemExit) as e:
        print(f"⚠️ CRITICAL ERROR: {e}")
        time.sleep(10)  
        print("🔄 Restarting now...")
        os.execv(sys.executable, ['python'] + sys.argv)
    finally:
        try:
            loop.close()
        except Exception:
            pass
