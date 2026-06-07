from shared_client import client as bot_client, app
from telethon import events, Button
from telethon.errors import FloodWaitError
from datetime import timedelta, datetime
import os
import psutil
import string
import random
from config import OWNER_ID
from utils.func import add_premium_user, is_private_chat, log_admin_activity, get_display_name
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton as IK, InlineKeyboardMarkup as IKM
from config import OWNER_ID, JOIN_LINK as JL , ADMIN_CONTACT as AC
import base64 as spy
from utils.func import a1, a2, a3, a4, a5, a7, a8, a9, a10, a11
from plugins.start import subscribe
import asyncio
from utils.db import premium_collection, users_collection, db

# 🟢 CANCEL KEYBOARD
cancel_kb = [Button.text("❌ Cancel", resize=True, single_use=True)]

# 🟢 SHARED ADMIN MENU BUTTONS (Ek hi jagah define kiya taaki hamesha sync rahe)
ADMIN_MENU_BUTTONS = [
    [Button.inline("➕ Add Premium", b"adm_add"), Button.inline("➖ Rem Premium", b"adm_rem")],
    [Button.inline("🎟 Gen Code", b"adm_gen"), Button.inline("📋 Get User List", b"adm_get")],
    [Button.inline("🔒 Lock Channel", b"adm_lock"), Button.inline("🛠 Fix Header", b"adm_fix")],
    [Button.inline("📊 Stats", b"adm_stats"), Button.inline("💘 Transfer", b"adm_trans")],
    [Button.inline("📢 Broadcast Message", b"adm_broadcast")],
    [Button.inline("❌ Close Panel", b"adm_close")]
]

# =========================================================
# START COMMAND (With Auto DB Save)
# =========================================================
attr1 = spy.b64encode("photo".encode()).decode()
attr2 = spy.b64encode("file_id".encode()).decode()

@app.on_message(filters.command(spy.b64decode(a5.encode()).decode()))
async def start_handler(client, message):
    # 🟢 Save User in Database on /start
    user_id = message.from_user.id
    await users_collection.update_one(
        {"_id": user_id},
        {"$setOnInsert": {"_id": user_id, "join_date": datetime.now()}},
        upsert=True
    )

    subscription_status = await subscribe(client, message)
    if subscription_status == 1: return
    b1, b2, b3, b4 = spy.b64decode(a1).decode(), int(spy.b64decode(a2).decode()), spy.b64decode(a3).decode(), spy.b64decode(a4).decode()
    b6, b7, b8, b9, b10 = spy.b64decode(a7).decode(), spy.b64decode(a8).decode(), spy.b64decode(a9).decode(), spy.b64decode(a10).decode(), spy.b64decode(a11).decode()
    tm = await getattr(app, b3)(b1, b2)
    pb = getattr(tm, spy.b64decode(attr1.encode()).decode())
    fd = getattr(pb, spy.b64decode(attr2.encode()).decode())
    kb = IKM([[IK(b7, url=JL)], [IK(b8, url=AC)]])
    await getattr(message, b4)(fd, caption=b6, reply_markup=kb)

# =========================================================
# PREMIUM MANUAL COMMANDS (/add, /rem, /transfer)
# =========================================================
@bot_client.on(events.NewMessage(pattern=r'(?i)^/add'))
async def add_premium_handler(event):
    if not await is_private_chat(event): return await event.respond('Private chats only.')
    user_id = event.sender_id
    if user_id not in OWNER_ID: return await event.respond('Restricted to bot owner.')
        
    parts = event.message.text.strip().split(' ')
    if len(parts) < 4:
        return await event.respond('❌ Format: `/add user_id duration unit` (e.g., `/add 12345 1 month`)')
    
    try:
        target_user_id = int(parts[1])
        duration_value = int(parts[2])
        duration_unit = parts[3].lower()
    except ValueError:
        return await event.respond('❌ Invalid user ID or duration value.')
            
    valid_units = ['min', 'hours', 'days', 'weeks', 'month', 'year', 'decades']
    if duration_unit not in valid_units: return await event.respond(f"❌ Invalid duration unit.")
        
    success, result = await add_premium_user(target_user_id, duration_value, duration_unit)
    if success:
        expiry_ist = result + timedelta(hours=5, minutes=30)
        await event.respond(f"✅ User {target_user_id} added.\nValid until: {expiry_ist.strftime('%d-%b-%Y %I:%M:%S %p')} (IST)")
        try: await bot_client.send_message(target_user_id, f"✅ You are now a premium member\n**Validity**: {expiry_ist.strftime('%d-%b-%Y %I:%M:%S %p')}")
        except: pass
    else:
        await event.respond(f'❌ Failed: {result}')

@bot_client.on(events.NewMessage(pattern=r'(?i)^/rem'))
async def rem_premium(event):
    if event.sender_id not in OWNER_ID: return await event.respond("❌ Only Owner.")
    parts = event.message.text.split(' ')
    if len(parts) < 2: return await event.respond("❌ Format: `/rem UserID`")
    target_id = int(parts[1])
    await premium_collection.delete_one({"user_id": target_id})
    await event.respond(f"✅ User `{target_id}` removed from premium.")

@bot_client.on(events.NewMessage(pattern=r'(?i)^/transfer'))
async def transfer_premium(event):
    uid = event.sender_id
    prem_user = await premium_collection.find_one({"user_id": uid})
    if not prem_user or prem_user.get("subscription_end") < datetime.now(): return await event.respond("❌ No active Premium Plan.")
    parts = event.message.text.split(' ')
    if len(parts) < 2: return await event.respond("❌ Format: `/transfer UserID`")
    target_id = int(parts[1])
    await premium_collection.update_one({"user_id": target_id}, {"$set": {"subscription_start": prem_user["subscription_start"], "subscription_end": prem_user["subscription_end"]}}, upsert=True)
    await premium_collection.delete_one({"user_id": uid})
    await event.respond(f"✅ Premium Transferred to `{target_id}`.")

# =========================================================
# OTHER COMMANDS (/stats, /get, /gen, /lock, /redeem)
# =========================================================
@bot_client.on(events.NewMessage(pattern=r'(?i)^/stats$'))
async def stats_command(event):
    if event.sender_id not in OWNER_ID: return
    msg = await event.respond("⏳ Fetching Statistics...")
    total_users = await users_collection.count_documents({})
    prem_users = await premium_collection.count_documents({})
    ram = psutil.virtual_memory().percent
    cpu = psutil.cpu_percent()
    disk = psutil.disk_usage('/').percent
    await msg.edit(f"📊 **Bot Statistics**\n\n👥 **Total Users:** `{total_users}`\n💎 **Premium Users:** `{prem_users}`\n\n🖥 **Server:**\n├ **CPU:** `{cpu}%`\n├ **RAM:** `{ram}%`\n└ **Disk:** `{disk}%`")

@bot_client.on(events.NewMessage(pattern=r'(?i)^/get$'))
async def get_users_command(event):
    if event.sender_id not in OWNER_ID: return
    msg = await event.respond("⏳ Extracting user list...")
    users = await users_collection.find({}, {"_id": 1}).to_list(length=None)
    with open("users.txt", "w") as f:
        for user in users: f.write(f"{user['_id']}\n")
    await bot_client.send_file(event.chat_id, "users.txt", caption=f"📁 **Total Users:** `{len(users)}`")
    await msg.delete()
    if os.path.exists("users.txt"): os.remove("users.txt")

@bot_client.on(events.NewMessage(pattern=r'(?i)^/gen'))
async def gen_code_command(event):
    if event.sender_id not in OWNER_ID: return
    parts = event.message.text.split(' ')
    if len(parts) < 3: return await event.respond("⚠️ Format: `/gen days uses`")
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
    await db["redeem_codes"].insert_one({"code": code, "days": int(parts[1]), "max_uses": int(parts[2]), "used_by": []})
    await event.respond(f"🎟 **Code:** `{code}`")

@bot_client.on(events.NewMessage(pattern=r'(?i)^/lock'))
async def lock_channel_command(event):
    if event.sender_id not in OWNER_ID: return
    parts = event.message.text.split(' ')
    if len(parts) < 2: return await event.respond("⚠️ Format: `/lock ChatID`")
    await db["locked_chats"].update_one({"chat_id": parts[1]}, {"$set": {"locked": True}}, upsert=True)
    await event.respond(f"✅ **Chat `{parts[1]}` Locked.**")

@bot_client.on(events.NewMessage(pattern=r'(?i)^/redeem'))
async def redeem_command(event):
    user_id = event.sender_id
    parts = event.message.text.split(' ')
    if len(parts) < 2: return await event.respond("⚠️ **Format:** `/redeem YOUR_CODE`")
    
    code_str = parts[1]
    code_data = await db["redeem_codes"].find_one({"code": code_str})
    if not code_data: return await event.respond("❌ **Invalid Code!**")
        
    used_by = code_data.get("used_by", [])
    if user_id in used_by: return await event.respond("⚠️ **Code already used!**")
        
    max_uses = code_data.get("max_uses", 1)
    if len(used_by) >= max_uses: return await event.respond("❌ **Expired!** Limit reached.")
        
    days = code_data.get("days", 0)
    prem_user = await premium_collection.find_one({"user_id": user_id})
    now = datetime.now()
    new_end = (prem_user["subscription_end"] + timedelta(days=days)) if prem_user and prem_user.get("subscription_end", now) > now else (now + timedelta(days=days))
        
    await premium_collection.update_one({"user_id": user_id}, {"$set": {"subscription_start": now, "subscription_end": new_end}}, upsert=True)
    await db["redeem_codes"].update_one({"code": code_str}, {"$push": {"used_by": user_id}})
    
    await event.respond(f"🎉 **Congratulations!**\n💎 **{days} Days** Premium Added.\n👑 **Valid Until:** `{new_end.strftime('%d-%b-%Y %I:%M %p')}`")

# =========================================================
# ADMIN PANEL TRIGGERS
# =========================================================
@bot_client.on(events.NewMessage(pattern=r'(?i)^/admin$'))
async def admin_dashboard(event):
    if not await is_private_chat(event): return
    if event.sender_id not in OWNER_ID: return await event.respond("❌ **Access Denied!**")
    await event.respond("👑 **Admin Command Center**\nSelect an action to perform:", buttons=ADMIN_MENU_BUTTONS)

@bot_client.on(events.CallbackQuery(pattern=b"^run_admin$"))
async def direct_admin_trigger(event):
    if event.sender_id not in OWNER_ID: return await event.answer("❌ Access Denied!", alert=True)
    await event.delete()
    await event.respond("👑 **Admin Command Center**\nSelect an action to perform:", buttons=ADMIN_MENU_BUTTONS)

# =========================================================
# UNIFIED CALLBACK HANDLER (MAGIC HAPPENS HERE)
# =========================================================
@bot_client.on(events.CallbackQuery(pattern=b"^adm_"))
async def admin_callbacks(event):
    if event.sender_id not in OWNER_ID: return await event.answer("Access Denied!", alert=True)
    action = event.data.decode('utf-8')

    # 1️⃣ UI NAVIGATION (Without deleting message)
    if action == "adm_back":
        return await event.edit("👑 **Admin Command Center**\nSelect an action to perform:", buttons=ADMIN_MENU_BUTTONS)

    elif action == "adm_stats":
        await event.edit("⏳ Fetching Statistics...")
        total_users = await users_collection.count_documents({})
        prem_users = await premium_collection.count_documents({})
        ram = psutil.virtual_memory().percent
        cpu = psutil.cpu_percent()
        disk = psutil.disk_usage('/').percent
        stats_text = (f"📊 **Bot Statistics**\n\n👥 **Total Users:** `{total_users}`\n💎 **Premium Users:** `{prem_users}`\n\n🖥 **Server Status:**\n├ **CPU Usage:** `{cpu}%`\n├ **RAM Usage:** `{ram}%`\n└ **Disk Usage:** `{disk}%`")
        return await event.edit(stats_text, buttons=[[Button.inline("◀️ Back", b"adm_back")]])

    elif action == "adm_broadcast":
        try:
            async with bot_client.conversation(event.chat_id, timeout=300) as conv:
                await conv.send_message("📢 **Smart Broadcast System**\n\n1️⃣ Apna message ya file bot ko yahan bhejo:", buttons=cancel_kb)
                broadcast_msg = await conv.get_response()

                if broadcast_msg.text in ["/cancel", "❌ Cancel"]:
                    return await event.respond("🚫 **Broadcast Cancelled.**", buttons=Button.clear())

                confirm_kb = [[Button.inline("✅ Confirm to Send", b"confirm_broadcast")], [Button.inline("❌ Cancel", b"cancel_broadcast")]]
                await conv.send_message("👀 **Preview:** Ye message sabhi users ko jayega.\n\nKya aap confirm karte hain?", reply_to=broadcast_msg.id, buttons=confirm_kb)
                
                press = await conv.wait_event(events.CallbackQuery(pattern=b"^(confirm_broadcast|cancel_broadcast)$"))

                if press.data == b"cancel_broadcast":
                    return await press.edit("🚫 **Broadcast Cancelled.**")

                await press.edit("⏳ **Broadcast Started!** Fetching users...")
                
                users = await users_collection.find({}, {"_id": 1}).to_list(length=None)
                total_users = len(users)

                if total_users == 0: return await press.edit("❌ Database me koi user nahi mila!")

                await press.edit(f"🚀 **Broadcasting to {total_users} users...**")
                success, failed = 0, 0

                for user in users:
                    target_id = user.get("_id")
                    if not target_id: continue
                    try:
                        await bot_client.send_message(target_id, broadcast_msg)
                        success += 1
                        await asyncio.sleep(0.1) 
                    except Exception:
                        failed += 1

                await press.edit(f"✅ **Broadcast Completed!** 📢\n\n📊 **Total Users:** `{total_users}`\n🚀 **Success:** `{success}`\n❌ **Failed:** `{failed}`")
                return
        except asyncio.TimeoutError:
            return await event.respond("⏳ **Timeout! Broadcast Cancelled.**", buttons=Button.clear())

    # 2️⃣ ACTION EXECUTIONS (These need conversation, so we delete the panel)
    await event.delete()

    if action == "adm_close":
        return

    elif action == "adm_get":
        msg = await event.respond("⏳ Extracting user list...")
        users = await users_collection.find({}, {"_id": 1}).to_list(length=None)
        file_path = "users.txt"
        with open(file_path, "w") as f:
            for user in users: f.write(f"{user['_id']}\n")
        await bot_client.send_file(event.chat_id, file_path, caption=f"📁 **Total Users:** `{len(users)}`")
        await msg.delete()
        if os.path.exists(file_path): os.remove(file_path)

    elif action == "adm_add":
        try:
            async with bot_client.conversation(event.chat_id, timeout=60) as conv:
                await conv.send_message("👤 **Enter User ID to add:**", buttons=cancel_kb)
                uid_msg = await conv.get_response()
                if uid_msg.text in ["/cancel", "❌ Cancel"]: return await event.respond("🚫 **Cancelled.**", buttons=Button.clear())
                
                await conv.send_message("🗓 **Enter duration value (e.g., 1, 5):**", buttons=cancel_kb)
                dur_val_msg = await conv.get_response()
                if dur_val_msg.text in ["/cancel", "❌ Cancel"]: return await event.respond("🚫 **Cancelled.**", buttons=Button.clear())
                
                await conv.send_message("⏳ **Enter duration unit (min, hours, days, weeks, month, year, decades):**", buttons=cancel_kb)
                dur_unit_msg = await conv.get_response()
                if dur_unit_msg.text in ["/cancel", "❌ Cancel"]: return await event.respond("🚫 **Cancelled.**", buttons=Button.clear())
                
                success, result = await add_premium_user(int(uid_msg.text), int(dur_val_msg.text), dur_unit_msg.text.lower())
                if success: await event.respond(f"✅ User added as premium member", buttons=Button.clear())
                else: await event.respond(f'❌ Failed: {result}', buttons=Button.clear())
        except Exception: await event.respond("Error/Timeout: Cancelled.", buttons=Button.clear())

    elif action == "adm_rem":
        try:
            async with bot_client.conversation(event.chat_id, timeout=60) as conv:
                await conv.send_message("👤 **Enter User ID to remove:**", buttons=cancel_kb)
                uid_msg = await conv.get_response()
                if uid_msg.text in ["/cancel", "❌ Cancel"]: return await event.respond("🚫 **Cancelled.**", buttons=Button.clear())
                
                await premium_collection.delete_one({"user_id": int(uid_msg.text)})
                await event.respond(f"✅ **Success!** User `{uid_msg.text}` removed.", buttons=Button.clear())
        except Exception: await event.respond("⏳ **Timeout!**", buttons=Button.clear())

    elif action == "adm_gen":
        try:
            async with bot_client.conversation(event.chat_id, timeout=60) as conv:
                await conv.send_message("🗓 **Enter Days for Premium Code:**", buttons=cancel_kb)
                days_msg = await conv.get_response()
                if days_msg.text in ["/cancel", "❌ Cancel"]: return await event.respond("🚫 **Cancelled.**", buttons=Button.clear())
                
                await conv.send_message("👥 **Enter Max Uses for this Code:**", buttons=cancel_kb)
                uses_msg = await conv.get_response()
                if uses_msg.text in ["/cancel", "❌ Cancel"]: return await event.respond("🚫 **Cancelled.**", buttons=Button.clear())
                
                code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
                await db["redeem_codes"].insert_one({"code": code, "days": int(days_msg.text), "max_uses": int(uses_msg.text), "used_by": []})
                await event.respond(f"🎟 **Premium Code Generated!**\n\n💳 **Code:** `{code}`\n🗓 **Days:** `{days_msg.text}`\n👥 **Max Uses:** `{uses_msg.text}`", buttons=Button.clear())
        except Exception: await event.respond("⏳ **Timeout!**", buttons=Button.clear())

    elif action == "adm_lock":
        try:
            async with bot_client.conversation(event.chat_id, timeout=60) as conv:
                await conv.send_message("🔒 **Enter Chat ID to Lock:**", buttons=cancel_kb)
                chat_msg = await conv.get_response()
                if chat_msg.text in ["/cancel", "❌ Cancel"]: return await event.respond("🚫 **Cancelled.**", buttons=Button.clear())
                
                await db["locked_chats"].update_one({"chat_id": chat_msg.text}, {"$set": {"locked": True}}, upsert=True)
                await event.respond(f"✅ **Chat `{chat_msg.text}` Locked.**", buttons=Button.clear())
        except Exception: await event.respond("⏳ **Timeout!**", buttons=Button.clear())

    elif action == "adm_fix": await event.respond("👉 **Manual Repair Mode**\nSend `/fix` in chat to start video repairing process.")
    elif action == "adm_trans": await event.respond("👉 Send `/transfer UserID` to transfer your plan.")