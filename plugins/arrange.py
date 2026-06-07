import os
import re
import time
import asyncio
import logging
import traceback
from pyrogram import filters, Client, StopPropagation
from pyrogram.errors import FloodWait  
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ChatMemberStatus

from utils.func import get_user_data_key, is_premium_user
from config import API_ID, API_HASH
from shared_client import app
from utils.encrypt import dcs

logger = logging.getLogger(__name__)

ARRANGE_STATE = {}
ARRANGE_ACTIVE_TASKS = {} 

cancel_markup = InlineKeyboardMarkup([
    [InlineKeyboardButton("🚫 Cancel", callback_data="cancel_arrange")]
])

def arrange_filter_func(_, __, message):
    return bool(message.from_user and message.from_user.id in ARRANGE_STATE)
arrange_filter = filters.create(arrange_filter_func)

IGNORE_CMDS = ["start", "help", "login", "logout", "single", "batch", "arrange", "dl", "adl", "forward", "settings", "id", "cancel", "redeem", "setbot", "rembot", "gen"]

# 🔥 FIX 1: StopPropagation lagaya taaki batch.py false error na de
@app.on_message(filters.command("cancel") & filters.private, group=-6)
async def stop_arrange_command(client, message):
    user_id = message.from_user.id
    if user_id in ARRANGE_ACTIVE_TASKS:
        ARRANGE_ACTIVE_TASKS[user_id] = False
        logger.info(f"[ARRANGE ENGINE] User {user_id} triggered /cancel")
        await message.reply("🛑 **Arrange Process Cancellation Requested!**\nKripya 10-15 seconds wait karein, bot current file ya sleep finish karke poori tarah ruk jayega.")
        raise StopPropagation

@app.on_message(filters.command("arrange") & filters.private)
async def arrange_command(client, message: Message):
    user_id = message.from_user.id
    if not await is_premium_user(user_id):
        return await message.reply("❌ **Ye feature sirf Premium users ke liye hai!**\nUpgrade to premium to use the Advanced Arrange Engine.")
    ARRANGE_STATE[user_id] = {"step": 1}
    await message.reply(
        "📦 **Advanced Channel Arranger**\n\nKripya **Source Channel ID** send karein (e.g., -100123456789):",
        reply_markup=cancel_markup
    )

@app.on_callback_query(filters.regex(r"^run_arrange$"))
async def arrange_callback(client, query):
    user_id = query.from_user.id
    if not await is_premium_user(user_id):
        return await query.answer("❌ Ye feature sirf Premium users ke liye hai! Upgrade karein.", show_alert=True)
    ARRANGE_STATE[user_id] = {"step": 1}
    await query.message.edit_text(
        "📦 **Advanced Channel Arranger**\n\nKripya **Source Channel ID** send karein (e.g., -100123456789):",
        reply_markup=cancel_markup
    )

@app.on_callback_query(filters.regex(r"^cancel_arrange$"))
async def cancel_arrange_callback(client, query):
    user_id = query.from_user.id
    if user_id in ARRANGE_STATE:
        del ARRANGE_STATE[user_id]
    if user_id in ARRANGE_ACTIVE_TASKS:
        ARRANGE_ACTIVE_TASKS[user_id] = False
    await query.message.edit_text("🚫 **Arrangement process cancelled!**\nBot ab neutral state me wapas aa gaya hai.")

@app.on_message(filters.private & filters.text & arrange_filter & ~filters.command(IGNORE_CMDS), group=-5)
async def arrange_conversation(client, message: Message):
    user_id = message.from_user.id
    
    try:
        state = ARRANGE_STATE.get(user_id)
        if not state:
            return
            
        step = state["step"]
        
        if step == 1:
            source_id = message.text.strip()
            try:
                source_id = int(source_id)
            except Exception as e:
                await message.reply("❌ **Invalid ID format!** Please send a valid numeric ID (e.g., -100123456789):", reply_markup=cancel_markup)
                raise StopPropagation 
                
            state["source_id"] = source_id
            state["step"] = 2
            await message.reply("✅ Source Channel ID Saved!\n\nAb kripya **Destination Group ID** send karein jahan Topics banenge:", reply_markup=cancel_markup)
            raise StopPropagation
            
        elif step == 2:
            dest_id = message.text.strip()
            try:
                dest_id = int(dest_id)
            except Exception as e:
                await message.reply("❌ **Invalid ID format!** Please send a valid numeric ID (e.g., -100123456789):", reply_markup=cancel_markup)
                raise StopPropagation
            
            enc_session = await get_user_data_key(user_id, "session_string")
            if not enc_session:
                del ARRANGE_STATE[user_id]
                await message.reply("❌ **Aapne account login nahi kiya hai!** Pehle `/login` command se apna session set karein.")
                raise StopPropagation
                
            try:
                session_string = dcs(enc_session)
            except Exception as e:
                session_string = enc_session
                
            wait_msg = await message.reply("⏳ Checking logic and permissions...")
            
            try:
                from plugins.batch import get_ubot
                ubot = await get_ubot(user_id)
                if not ubot:
                    del ARRANGE_STATE[user_id]
                    await wait_msg.edit("❌ **Aapne Custom Bot set nahi kiya hai!** Pehle `/setbot` use karke apna bot add karein tabhi Arrange Engine kaam karega.")
                    raise StopPropagation
                
                # 🔥 FIX 2: RAM Session & Unique Name (Taaki SQLite Crash na ho!)
                user_client = Client(f"temp_arranger_{user_id}", session_string=session_string, api_id=API_ID, api_hash=API_HASH, in_memory=True)
                await user_client.start()
                
                try:
                    user_member = await user_client.get_chat_member(dest_id, "me")
                    if user_member.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
                        await user_client.stop()
                        del ARRANGE_STATE[user_id]
                        await wait_msg.edit("❌ **Your User Session is not an ADMIN in the destination group.** Create topic rights are required.")
                        raise StopPropagation
                except Exception as e:
                    await user_client.stop()
                    del ARRANGE_STATE[user_id]
                    await wait_msg.edit(f"❌ **Your User Session is not added in the destination group.**\nDebug: `{e}`")
                    raise StopPropagation
                    
                await wait_msg.edit("✅ Permissions Verified! Fetching messages... Please wait.")
                
                ARRANGE_ACTIVE_TASKS[user_id] = True
                asyncio.create_task(start_arranging(ubot, user_client, state["source_id"], dest_id, wait_msg, user_id))
                del ARRANGE_STATE[user_id] 
                
            except StopPropagation:
                raise 
            except Exception as e:
                if user_id in ARRANGE_STATE: del ARRANGE_STATE[user_id]
                await wait_msg.edit(f"❌ System Crash (Validation): `{e}`")
                
    except StopPropagation:
        raise
    except Exception as final_e:
        await message.reply(f"🚨 **CRITICAL ERROR DETECTED:**\n`{final_e}`", reply_markup=cancel_markup)
    
    raise StopPropagation

async def start_arranging(bot_client, user_client, source_id, dest_id, status_msg, user_id):
    try:
        all_messages = []
        await status_msg.edit("🔍 **Fetching all messages using User Session...**")
        async for msg in user_client.get_chat_history(source_id):
            if msg.empty: continue
            all_messages.append(msg)
            
        all_messages.reverse()
        total_msgs = len(all_messages)
        
        if total_msgs == 0:
            await user_client.stop()
            return await status_msg.edit("❌ Source channel me koi message nahi mila!")
            
        created_topics = {} 
        needs_pin = {} 
        skipped_links = []
        chat_id_str = str(source_id).replace("-100", "") 
        
        await status_msg.edit("🔍 **Scanning existing topics...**")
        try:
            async for topic in user_client.get_forum_topics(dest_id):
                created_topics[topic.title.lower()] = topic.id
        except Exception:
            pass

        # ⚡ RAM PRE-PROCESSING (Files ko pehle hi topics ke hisaab se group karna)
        categorized_messages = {}
        skipped_count = 0
        
        for msg in all_messages:
            caption = msg.caption or msg.text or ""
            if not caption and not msg.media:
                skipped_count += 1
                skipped_links.append(f"https://t.me/c/{chat_id_str}/{msg.id}  (Reason: No Media & No Caption)")
                continue

            topic_match = re.search(r"(?:Topic|Subject)[^:]*:\s*(.+)", caption, re.IGNORECASE)
            topic_name = topic_match.group(1).strip() if topic_match else "Uncategorized Files"
            
            if topic_name not in categorized_messages:
                categorized_messages[topic_name] = []
            categorized_messages[topic_name].append(msg.id)

        processed_count = 0
        last_update_time = time.time()
        
        await status_msg.edit(f"🛡️ **Starting Ultra-Safe Arrangement Engine**\nTotal Files: {total_msgs}\n\nProgress: 0%")

        for topic_name, msg_ids in categorized_messages.items():
            if not ARRANGE_ACTIVE_TASKS.get(user_id, True):
                break
                
            topic_key = topic_name.lower()
            
            if topic_key not in created_topics:
                try:
                    new_topic = await user_client.create_forum_topic(chat_id=dest_id, title=topic_name)
                    created_topics[topic_key] = new_topic.id
                    needs_pin[topic_key] = True 
                except Exception as e:
                    logger.error(f"Failed to create topic '{topic_name}': {e}")
                    created_topics[topic_key] = None 
                    
            thread_id = created_topics[topic_key]
            
            # 🔥 1-BY-1 LOOP WITH ULTRA-SAFE TIMING 🔥
            for index, mid in enumerate(msg_ids):
                if not ARRANGE_ACTIVE_TASKS.get(user_id, True):
                    break
                    
                success = False
                for attempt in range(3):
                    try:
                        m = await bot_client.copy_message(
                            chat_id=dest_id, 
                            from_chat_id=source_id, 
                            message_id=mid, 
                            message_thread_id=thread_id
                        )
                        processed_count += 1
                        success = True
                        
                        # 📌 PINNING MAGIC (Pehle message ko topic me pin karna) 📌
                        if index == 0 and needs_pin.get(topic_key):
                            try:
                                await bot_client.pin_chat_message(chat_id=dest_id, message_id=m.id)
                                needs_pin[topic_key] = False
                            except Exception: pass
                        break
                    except FloodWait as fw:
                        logger.warning(f"FloodWait! Sleeping for {fw.value + 2}s")
                        await asyncio.sleep(fw.value + 2)
                    except Exception as e:
                        logger.error(f"Copy Error: {e}")
                        break
                        
                if not success:
                    skipped_count += 1
                    skipped_links.append(f"https://t.me/c/{chat_id_str}/{mid}  (Reason: Copy Failed / Error)")
                
                # 🟢 SAFE TIMING (1.5s delay per file) 🟢
                await asyncio.sleep(1.5) 
                
                # 🟢 SAFE BREAK (15s delay after every 10 files) 🟢
                if processed_count > 0 and processed_count % 10 == 0:
                    logger.info("Taking 15s safe break to prevent Ban/FloodWait...")
                    await asyncio.sleep(15)

                # 🟢 PROGRESS BAR UPDATE (Har 15 sec me update taaki MessageEdit FloodWait na aaye) 🟢
                if time.time() - last_update_time >= 15:
                    percent = round((processed_count + skipped_count) / total_msgs * 100, 2)
                    progress_text = (
                        f"🛡️ **Arranging Files... (Ultra-Safe Mode)**\n"
                        f"📦 **Processed:** {processed_count + skipped_count}/{total_msgs} ({percent}%)\n"
                        f"✅ **Arranged:** {processed_count}\n"
                        f"⏭ **Skipped/Errors:** {skipped_count}\n"
                        f"📂 **Current Topic:** `{topic_name}`"
                    )
                    try:
                        await status_msg.edit(progress_text)
                    except Exception:
                        pass 
                    last_update_time = time.time()
                
        if ARRANGE_ACTIVE_TASKS.get(user_id, True):
            await status_msg.edit(
                f"🎉 **Arrangement Complete! (100% Safe 🛡️)**\n\n"
                f"✅ **Total Arranged:** {processed_count}\n"
                f"⏭ **Skipped/Errors:** {skipped_count}\n"
                f"📂 **Topics in Database:** {len(created_topics)}\n"
                f"👑 **Task Completed Seamlessly**"
            )
            
            if skipped_links:
                file_name = f"Skipped_Files_Report_{user_id}_{int(time.time())}.txt"
                try:
                    with open(file_name, "w", encoding="utf-8") as f:
                        f.write("⚠️ SKIPPED FILES REPORT ⚠️\n")
                        f.write(f"Total Skipped: {skipped_count}\n")
                        f.write("-" * 40 + "\n\n")
                        f.write("\n".join(skipped_links))
                        f.write("\n\n" + "-" * 40 + "\n👑 Generated by Advanced Arrange Engine")
                    
                    await status_msg.reply_document(
                        document=file_name,
                        caption="📄 **Ye rahi un sabhi skipped files ki list jo copy nahi ho payi.**\nAap link par click karke inhe manually check kar sakte hain."
                    )
                except Exception as e:
                    logger.error(f"Failed to send skipped list txt: {e}")
                finally:
                    if os.path.exists(file_name):
                        os.remove(file_name)
        else:
            await status_msg.edit(
                f"🛑 **Arrangement Stopped by User!**\n\n"
                f"✅ **Total Arranged:** {processed_count}\n"
                f"⏭ **Skipped:** {skipped_count}"
            )
            
    except Exception as e:
        logger.error(f"[ARRANGE TASK] FATAL LOOP ERROR: {e}\n{traceback.format_exc()}")
        await status_msg.edit(f"❌ Error during arrangement: `{e}`")
    finally:
        if user_id in ARRANGE_ACTIVE_TASKS:
            del ARRANGE_ACTIVE_TASKS[user_id]
        # 🔥 FIX 3: Pyrogram background disconnect exception handled gracefully
        try:
            await user_client.stop()
        except Exception:
            pass