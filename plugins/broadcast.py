import asyncio
import logging
from pyrogram import filters
from pyrogram.errors import FloodWait, InputUserDeactivated, UserIsBlocked
from shared_client import app
from config import OWNER_ID
from utils.db import users_collection

logger = logging.getLogger(__name__)

# ======================================================================
# 🟢 SMART BROADCAST SYSTEM (Admin Power)
# ======================================================================
@app.on_message(filters.command("broadcast") & filters.private)
async def broadcast_command(client, message):
    user_id = message.from_user.id
    
    # 1. Sirf Owner (Admin) access kar sakta hai
    if user_id not in OWNER_ID:
        return await message.reply_text("❌ **Access Denied!** Ye command sirf Bot Owner ke liye hai.")

    # 2. Check karna ki kisi message ka reply kiya hai ya nahi
    if not message.reply_to_message:
        return await message.reply_text(
            "⚠️ **Format Error!**\n\n"
            "Broadcast karne ke liye pehle apna message bhejen (Text, Photo, Video, ya File), "
            "phir us message ko **reply** karte hue likhein:\n👉 `/broadcast`"
        )

    # 3. Status message
    b_msg = await message.reply_text("⏳ **Broadcast Started!**\nDatabase se users ki list nikali ja rahi hai...")
    
    # 4. Database se saare users uthana
    users = await users_collection.find({}, {"user_id": 1}).to_list(length=None)
    total_users = len(users)
    
    if total_users == 0:
        return await b_msg.edit("❌ Database me koi user nahi mila!")

    await b_msg.edit(f"🚀 **Broadcasting to {total_users} users...**\nKripya thoda wait karein, isme time lag sakta hai.")

    success = 0
    failed = 0
    
    # 5. Har user ko message bhejna (with Anti-Spam protection)
    for user in users:
        target_id = user.get("user_id")
        if not target_id:
            continue
            
        try:
            # Message Copy karega (Isse forward tag nahi aayega, aur button/media sab safe rahenge)
            await message.reply_to_message.copy(chat_id=int(target_id))
            success += 1
            await asyncio.sleep(0.1)  # 🛑 API Spam se bachne ke liye chhota delay
            
        except FloodWait as e:
            # Agar Telegram block kare toh utne second wait karega
            await asyncio.sleep(e.value + 1)
            try:
                await message.reply_to_message.copy(chat_id=int(target_id))
                success += 1
            except:
                failed += 1
                
        except (InputUserDeactivated, UserIsBlocked):
            # Agar user ne bot block kar diya ya account delete kar diya
            failed += 1
            # Optional: Tum chaho toh in 'dead' users ko DB se delete bhi karwa sakte ho aage chal ke
            
        except Exception as e:
            failed += 1

    # 6. Final Report
    report = (
        f"✅ **Broadcast Successfully Completed!** 📢\n\n"
        f"📊 **Total Users in DB:** `{total_users}`\n"
        f"🚀 **Successfully Sent:** `{success}`\n"
        f"❌ **Failed (Blocked/Deleted):** `{failed}`\n"
    )
    
    await b_msg.edit(report)