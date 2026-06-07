import asyncio
import logging
import random
import time
from pyrogram import filters
from pyrogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from shared_client import app
from utils.func import is_premium_user, get_user_data_key, save_user_data
from config import OWNER_ID
from utils.db import db

# 🟢 IMPORT POWERFUL ENGINES FROM BATCH.PY (For Userbot & Restricted Handling)
from plugins.batch import get_uclient, get_ubot, process_msg, get_user_lock

logger = logging.getLogger(__name__)

# Database collection for AutoSync
autosync_col = db["autosync"]

# 🟢 CANCEL KEYBOARD
cancel_kb = ReplyKeyboardMarkup([[KeyboardButton("❌ Cancel")]], resize_keyboard=True, one_time_keyboard=True)

# 🟢 IN-MEMORY TRACKER (1 Channel Per Hour)
USER_LAST_CHECK = {}

# ======================================================================
# 🚀 THE REAL ENGINE: ROUND-ROBIN BACKGROUND SCANNER
# ======================================================================
async def process_single_sync(sync):
    user_id = sync.get("user_id")
    src_id_int = int(sync.get("source_id"))
    tgt_id_int = int(sync.get("target_id"))
    last_msg_id = sync.get("last_msg_id", 0)

    uc = await get_uclient(user_id)
    ubot = await get_ubot(user_id)
    client_to_use = uc if uc else ubot
    
    if not client_to_use: return

    latest_msgs = []
    # Check max 15 recent messages per hour to avoid flood
    async for msg in client_to_use.get_chat_history(src_id_int, limit=15):
        if msg.id > last_msg_id:
            latest_msgs.append(msg)
        else:
            break
    
    if latest_msgs:
        latest_msgs.sort(key=lambda x: x.id) # Purane se naya order maintain karne ke liye

        # User ki specific settings nikalna jo usne AutoSync set karte time di thi
        task_data = {
            "source": str(src_id_int), 
            "destination": str(tgt_id_int), 
            "dest_id": str(tgt_id_int),
            "remove_list": sync.get("remove_list", []),
            "replace_dict": sync.get("replace_dict", {}),
            "watermark": sync.get("watermark", ""),
            "custom_name": await get_user_data_key(user_id, "custom_name", "🇮‌🇹‌'🇸‌ 🇭‌4⃣🇷‌"),
            "custom_template": await get_user_data_key(user_id, "custom_template", None)
        }
        
        # 🛑 QUEUE SYSTEM: Agar normal batch chal raha hai ya pehla sync msg process ho raha hai, toh dusra wait karega
        user_lock = get_user_lock(user_id)
        
        for msg in latest_msgs:
            await user_lock.acquire() 
            try:
                await process_msg(
                    c=ubot if ubot else app, 
                    u=uc, 
                    m=msg, 
                    d=tgt_id_int, 
                    lt='private' if str(src_id_int).startswith('-100') else 'public', 
                    uid=user_id, 
                    i=src_id_int, 
                    task=task_data
                )
            finally:
                user_lock.release() 
            
            # Database me msg id save karo taaki repeat na ho
            await autosync_col.update_one({"_id": sync["_id"]}, {"$set": {"last_msg_id": msg.id}})
            await asyncio.sleep(random.uniform(15.5, 25.2)) # Anti-ban delay


async def autosync_scanner():
    await asyncio.sleep(15)
    while True:
        try:
            users = await autosync_col.distinct("user_id")
            now = time.time()
            
            for uid in users:
                # 🗑️ SMART GARBAGE COLLECTION & SECURITY 🗑️
                # Agar user ka premium expire ho gaya hai, toh uske saare AutoSync DB se uda do!
                if not await is_premium_user(uid):
                    await autosync_col.delete_many({"user_id": uid})
                    continue # Is user ko skip karke agle par jao

                # 🟢 RULE: Ek user ka koi bhi channel 1 hour me ek baar...
                last_check = USER_LAST_CHECK.get(uid, 0)
                
                if now - last_check >= 3600:
                    # Find the sync task that was checked the longest time ago (Round-Robin Logic)
                    sync = await autosync_col.find_one(
                        {"user_id": uid},
                        sort=[("last_checked_time", 1)]
                    )
                    
                    if sync:
                        try:
                            await process_single_sync(sync)
                        except Exception as e:
                            logger.error(f"Sync error for user {uid}: {e}")
                        
                        # 🟢 Update timers: Ab is user ka agla channel theek 1 ghante baad check hoga
                        USER_LAST_CHECK[uid] = time.time()
                        await autosync_col.update_one({"_id": sync["_id"]}, {"$set": {"last_checked_time": time.time()}})
                        
        except Exception as e:
            logger.error(f"AutoSync Scanner Error: {e}")
        
        # Har 1 minute me loop check karega ki kisi user ka 1 ghanta poora hua ya nahi
        await asyncio.sleep(60)

# Start the scanner loop in background automatically
asyncio.get_event_loop().create_task(autosync_scanner())


# ======================================================================
# 🟢 DIRECT BUTTON EXECUTION FOR AUTOSYNC (Conversational Flow)
# ======================================================================
@app.on_callback_query(filters.regex("^(run_autosync|run_delsync)$"))
async def direct_sync_trigger(client, query):
    user_id = query.from_user.id
    cmd = query.data.replace("run_", "")
    await query.message.delete()
    
    if not await is_premium_user(user_id) and user_id not in OWNER_ID:
        return await client.send_message(query.message.chat.id, "❌ **Premium Feature!**\nAutoSync set karne ke liye Premium kharidein.")

    if cmd == "autosync":
        try:
            # 🟢 1. LIMIT CHECK (Max 5 Syncs)
            sync_count = await autosync_col.count_documents({"user_id": user_id})
            if sync_count >= 5:
                return await client.send_message(query.message.chat.id, "❌ **Limit Reached!**\nAap maximum 5 AutoSync channels set kar chuke hain.")

            # 🟢 2. SOURCE ID
            source_msg = await client.ask(
                query.message.chat.id, 
                "🔄 **AutoSync Setup (Step 1/5)**\n\n📢 Kripya **Source Channel ka ID** bhejen jahan se clone karna hai:\n_(Example: -100123456789)_",
                reply_markup=cancel_kb, timeout=120
            )
            if source_msg.text in ["/cancel", "❌ Cancel"]: return await client.send_message(query.message.chat.id, "🚫 **Cancelled.**", reply_markup=ReplyKeyboardRemove())
            source_id = source_msg.text.strip()
            int(source_id)

            # 🟢 3. REMOVE WORDS
            rm_msg = await client.ask(
                query.message.chat.id, 
                "📝 **Step 2/5: Words to Remove**\nEnter words you want to remove from caption (comma separated).\n\n🔹 Type `/d` for Default\n🔹 Type `0` for Previous\n🔹 Type `/s` to Skip", 
                reply_markup=cancel_kb, timeout=120
            )
            if rm_msg.text in ["/cancel", "❌ Cancel"]: return await client.send_message(query.message.chat.id, "🚫 **Cancelled.**", reply_markup=ReplyKeyboardRemove())
            text_lower = rm_msg.text.strip().lower()
            if text_lower in ['/d', 'd']: resolved_remove = await get_user_data_key(user_id, "delete_words", [])
            elif text_lower == '0': resolved_remove = await get_user_data_key(user_id, "last_remove", [])
            elif text_lower in ['/s', 's']: resolved_remove = []
            else: resolved_remove = [w.strip() for w in rm_msg.text.strip().split(',')]
            await save_user_data(user_id, "last_remove", resolved_remove)

            # 🟢 4. REPLACE WORDS
            rep_msg = await client.ask(
                query.message.chat.id, 
                "🔄 **Step 3/5: Words to Replace**\nEnter words to rename. Format: `old_word | new_word`\n\n🔹 Type `/d` for Default\n🔹 Type `0` for Previous\n🔹 Type `/s` to Skip", 
                reply_markup=cancel_kb, timeout=120
            )
            if rep_msg.text in ["/cancel", "❌ Cancel"]: return await client.send_message(query.message.chat.id, "🚫 **Cancelled.**", reply_markup=ReplyKeyboardRemove())
            text_lower = rep_msg.text.strip().lower()
            if text_lower in ['/d', 'd']: resolved_replace = await get_user_data_key(user_id, "replacement_words", {})
            elif text_lower == '0': resolved_replace = await get_user_data_key(user_id, "last_replace", {})
            elif text_lower in ['/s', 's']: resolved_replace = {}
            else:
                try:
                    old_w, new_w = rep_msg.text.strip().split('|')
                    resolved_replace = {old_w.strip(): new_w.strip()}
                except: resolved_replace = {}
            await save_user_data(user_id, "last_replace", resolved_replace)

            # 🟢 5. WATERMARK
            wm_msg = await client.ask(
                query.message.chat.id, 
                "🖼️ **Step 4/5: Thumbnail Watermark**\nEnter the text for Watermark.\n\n🔹 Type `/d` for Default\n🔹 Type `0` for Previous\n🔹 Type `/s` to Skip", 
                reply_markup=cancel_kb, timeout=120
            )
            if wm_msg.text in ["/cancel", "❌ Cancel"]: return await client.send_message(query.message.chat.id, "🚫 **Cancelled.**", reply_markup=ReplyKeyboardRemove())
            text_lower = wm_msg.text.strip().lower()
            if text_lower in ['/d', 'd']: resolved_wm = await get_user_data_key(user_id, "watermark", "")
            elif text_lower == '0': resolved_wm = await get_user_data_key(user_id, "last_wm", "")
            elif text_lower in ['/s', 's']: resolved_wm = "skip"
            else: resolved_wm = wm_msg.text.strip()
            await save_user_data(user_id, "last_wm", resolved_wm)

            # 🟢 6. TARGET ID
            tgt_msg = await client.ask(
                query.message.chat.id, 
                "🎯 **Step 5/5: Target Channel ID**\nEnter the Chat ID where you want to send files.\n\n🔹 Type `/d` for Default\n🔹 Type `0` for Previous", 
                reply_markup=cancel_kb, timeout=120
            )
            if tgt_msg.text in ["/cancel", "❌ Cancel"]: return await client.send_message(query.message.chat.id, "🚫 **Cancelled.**", reply_markup=ReplyKeyboardRemove())
            text_lower = tgt_msg.text.strip().lower()
            if text_lower in ['/d', 'd']: 
                cfg_chat = await get_user_data_key(user_id, 'chat_id', None)
                target_id = cfg_chat.split('/')[0] if cfg_chat and '/' in cfg_chat else str(query.message.chat.id)
            elif text_lower == '0': target_id = await get_user_data_key(user_id, "last_chat", str(query.message.chat.id))
            else: target_id = tgt_msg.text.strip()
            await save_user_data(user_id, "last_chat", target_id)
            int(target_id)
            
            # Fetch current latest message ID to start syncing from NOW
            client_to_use = await get_uclient(user_id) or await get_ubot(user_id)
            last_msg_id = 0
            if client_to_use:
                try:
                    async for m in client_to_use.get_chat_history(int(source_id), limit=1):
                        last_msg_id = m.id
                except Exception: pass

            # 🟢 SAVE TO DATABASE
            await autosync_col.update_one(
                {"user_id": user_id, "source_id": str(source_id)},
                {"$set": {
                    "target_id": str(target_id), 
                    "last_msg_id": last_msg_id,
                    "remove_list": resolved_remove,
                    "replace_dict": resolved_replace,
                    "watermark": resolved_wm,
                    "last_checked_time": 0 # New h, jaldi check hoga
                }},
                upsert=True
            )
            
            # Agar bot just start hua hai, to pehla channel seedha check kar lenge bina 1 hour wait kiye
            if user_id not in USER_LAST_CHECK:
                USER_LAST_CHECK[user_id] = 0

            await client.send_message(
                query.message.chat.id, 
                f"✅ **AutoSync Successfully Set! ({sync_count + 1}/5)**\n\n📢 **Source:** `{source_id}`\n🎯 **Target:** `{target_id}`\n\nAb source me aane wala naya message tumhare custom rules (Watermark, Rename, etc.) ke sath queue me lag ke automatically aage jayega!", 
                reply_markup=ReplyKeyboardRemove()
            )

        except asyncio.TimeoutError:
            await client.send_message(query.message.chat.id, "⏳ **Timeout!** Aapne reply karne me zyada time laga diya. Operation cancelled.", reply_markup=ReplyKeyboardRemove())
        except ValueError:
            await client.send_message(query.message.chat.id, "❌ **Invalid ID!** Source aur Target ID numbers hone chahiye (with '-' if channel).", reply_markup=ReplyKeyboardRemove())
        except Exception as e:
            await client.send_message(query.message.chat.id, f"❌ **Error:** {e}", reply_markup=ReplyKeyboardRemove())

    elif cmd == "delsync":
        try:
            source_msg = await client.ask(
                query.message.chat.id, 
                "🛑 **Remove AutoSync**\n\n📢 Kripya wo **Source Channel ka ID** bhejen jise aap AutoSync se hatana chahte hain:",
                reply_markup=cancel_kb, timeout=120
            )
            if source_msg.text in ["/cancel", "❌ Cancel"]:
                return await client.send_message(query.message.chat.id, "🚫 **Operation Cancelled.**", reply_markup=ReplyKeyboardRemove())
            source_id = source_msg.text.strip()

            result = await autosync_col.delete_one({"user_id": user_id, "source_id": str(source_id)})
            
            if result.deleted_count > 0:
                await client.send_message(query.message.chat.id, f"🛑 **AutoSync Removed!**\nChannel `{source_id}` se ab koi message aage forward nahi hoga.", reply_markup=ReplyKeyboardRemove())
            else:
                await client.send_message(query.message.chat.id, f"❌ **Not Found!**\nIs Source ID `{source_id}` ke liye koi active AutoSync list me nahi mila.", reply_markup=ReplyKeyboardRemove())
        
        except asyncio.TimeoutError:
            await client.send_message(query.message.chat.id, "⏳ **Timeout!** Operation cancelled.", reply_markup=ReplyKeyboardRemove())
        except Exception as e:
            await client.send_message(query.message.chat.id, f"❌ **Error:** {e}", reply_markup=ReplyKeyboardRemove())


# ======================================================================
# 🟢 NORMAL TEXT COMMANDS
# ======================================================================
@app.on_message(filters.command("autosync") & filters.private)
async def set_autosync_cmd(client, message):
    await message.reply_text("⚠️ **Tip:** /autosync command ab directly kaam nahi karta kyunki isme bohot saari custom settings aa gayi hain. Kripya Help Menu me jakar **'🔄 AutoSync'** button dabayein taaki bot aapse step-by-step setup karwa sake!")

@app.on_message(filters.command("delsync") & filters.private)
async def del_autosync_cmd(client, message):
    user_id = message.from_user.id
    if len(message.command) == 2:
        source_id = message.command[1]
        result = await autosync_col.delete_one({"user_id": user_id, "source_id": str(source_id)})
        if result.deleted_count > 0:
            await message.reply_text(f"🛑 **AutoSync Removed!**\nChannel `{source_id}` se ab koi message forward nahi hoga.")
        else:
            await message.reply_text(f"❌ **Not Found!**\nIs Source ID `{source_id}` ke liye koi active AutoSync nahi mila.")
    else:
        await message.reply_text("⚠️ **Tip:** Aap sidha Help menu me `🛑 DelSync` button daba kar is feature ko aasani se use kar sakte hain!")

@app.on_message(filters.command("allsync") & filters.private)
async def list_autosync(client, message):
    user_id = message.from_user.id
    syncs = await autosync_col.find({"user_id": user_id}).to_list(length=None)
    
    if not syncs:
        return await message.reply_text("📂 Aapka koi AutoSync active nahi hai.")
        
    text = f"🔄 **Your Active AutoSyncs ({len(syncs)}/5):**\n\n"
    for s in syncs:
        text += f"📢 **Source:** `{s.get('source_id')}`\n🎯 **Target:** `{s.get('target_id')}`\n📝 **Rules:** {len(s.get('remove_list', []))} Remove, {len(s.get('replace_dict', {}))} Replace\n──────────────\n"
        
    await message.reply_text(text)