from telethon import events
import os
from shared_client import client
from utils.db import save_user_cookie 

@client.on(events.NewMessage(pattern="/setcookie (yt|insta)"))
async def handle_add_cookie(event):
    user_id = event.sender_id
    platform = event.pattern_match.group(1) 
    
    if not event.is_reply:
        return await event.reply(
            "**❌ Error:** Kripya apni `cookies.txt` file bhejein, aur uspe reply karke likhein:\n"
            "`/setcookie yt` (YouTube ke liye) ya\n"
            "`/setcookie insta` (Instagram ke liye)"
        )
        
    reply_msg = await event.get_reply_message()
    
    if not reply_msg.document or not reply_msg.file.name.endswith('.txt'):
        return await event.reply("**❌ Error:** Sirf `.txt` format me cookies file allow hai.")
        
    prog = await event.reply("**⏳ Cookies save ho rahi hain...**")
    
    file_path = await reply_msg.download_media()
    try:
        # utf-8-sig hidden characters ko hata dega
        with open(file_path, "r", encoding="utf-8-sig") as f:
            cookie_text = f.read().strip() # .strip() extra spaces/lines hata dega
            
        # Agar header missing hai toh bot khud laga dega
        if platform == "yt" and not cookie_text.startswith("#"):
            cookie_text = "# Netscape HTTP Cookie File\n\n" + cookie_text
            
        await save_user_cookie(user_id, platform, cookie_text)
        await prog.edit(f"**✅ Aapki {platform.upper()} cookies successfully database me save ho gayi hain!**\nAb aap apne links download kar sakte hain.")
        
    except Exception as e:
        await prog.edit(f"**❌ Error reading file:** `{e}`")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)