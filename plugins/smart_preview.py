import re
import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from shared_client import app as X
from utils.func import ai_rewrite_caption, get_user_data_key, process_text_with_rules

logger = logging.getLogger(__name__)

async def send_smart_preview(client, uid, Z, UB, UC):
    try:
        task_data = Z[uid].get('task_data', {})
        pt = Z[uid].get('pt')
        i = Z[uid]['cid']
        s_id = Z[uid]['sid']
        lt = Z[uid]['lt']
        
        ubot = UB.get(uid)
        uc = UC.get(uid)

        # Lazy import (taki circular error na aaye)
        from plugins.batch import get_msg 
        
        try:
            await pt.edit_text("⏳ **Smart Preview:** AI is generating caption for the first file...")
        except Exception:
            # Agar cache clear ho gaya toh naya message bhej do aur reference update kar do
            pt = await client.send_message(uid, "⏳ **Smart Preview:** AI is generating caption for the first file...")
            Z[uid]['pt'] = pt
        
        first_msg = await get_msg(ubot, uc, i, int(s_id), lt)
        
        if first_msg and (first_msg.caption or first_msg.text):
            raw_text = first_msg.caption.markdown if first_msg.caption else first_msg.text.markdown
            proc_text = await process_text_with_rules(uid, raw_text)
            user_cap = await get_user_data_key(uid, 'caption', '')
            raw_caption = f'{proc_text}\n\n{user_cap}' if proc_text and user_cap else user_cap if user_cap else proc_text
            
            # Apply task rules
            for word in task_data.get("remove_list", []): 
                raw_caption = re.sub(re.escape(word), "", raw_caption, flags=re.IGNORECASE)
            for old_w, new_w in task_data.get("replace_dict", {}).items(): 
                raw_caption = re.sub(re.escape(old_w), new_w, raw_caption, flags=re.IGNORECASE)
            
            raw_caption = re.sub(r'\.(mp4|mkv|pdf|avi|webm|jpg|png)', '', raw_caption, flags=re.IGNORECASE)
            raw_caption = re.sub(r'(?i)Number Of Digits', 'No. of Digit', raw_caption)

            extractor_name = await get_user_data_key(uid, "extractor_name", "🇮‌🇹‌'🇸‌ 🇭‌4⃣🇷‌")
            if not extractor_name or extractor_name.strip() == "":
                extractor_name = "🇮‌🇹‌'🇸‌ 🇭‌4⃣🇷‌"
                
            preview_caption = await ai_rewrite_caption(raw_caption, "", extractor_name)
            
            # Save data for regeneration
            Z[uid]['preview_raw'] = raw_caption
            Z[uid]['extractor_name'] = extractor_name

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Approve (Start Batch)", callback_data="prev_approve")],
                [InlineKeyboardButton("🔄 Regenerate AI Caption", callback_data="prev_regen")],
                [InlineKeyboardButton("✏️ Manual Edit", callback_data="prev_edit"),
                 InlineKeyboardButton("⏭️ Skip AI", callback_data="prev_skip")]
            ])
            
            await pt.edit(
                f"👀 **Smart Preview: AI Generated Caption**\n\n"
                f"Dekh lo bhai, batch start hone se pehle pehli file ka caption kaisa lag raha hai:\n\n"
                f"<code>{preview_caption}</code>\n\n"
                f"👇 Action choose karo:",
                reply_markup=keyboard
            )
        else:
            # Agar text nahi hai toh direct batch start kar do
            from plugins.batch import start_actual_batch
            await pt.edit("⚠️ No text found in first message. Starting batch directly...")
            await start_actual_batch(client, uid)

    except Exception as e:
        logger.error(f"Preview fetch error: {e}")
        from plugins.batch import start_actual_batch
        await start_actual_batch(client, uid)


@X.on_callback_query(filters.regex(r"^prev_"))
async def smart_preview_callbacks(client, query):
    uid = query.from_user.id
    action = query.data
    
    # Access global variables from batch.py safely
    from plugins.batch import Z, start_actual_batch
    
    if uid not in Z or 'task_data' not in Z[uid]:
        return await query.answer("Session expired! Please start the batch again.", show_alert=True)
        
    if action == "prev_approve":
        await query.message.edit_text("✅ **Preview Approved!**\n\n🚀 Starting batch extraction process now...")
        await start_actual_batch(client, uid)
        
    elif action == "prev_regen":
        await query.answer("🔄 Regenerating AI Caption... Please wait.", show_alert=False)
        preview_caption = await ai_rewrite_caption(Z[uid]['preview_raw'], "", Z[uid]['extractor_name'])
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Approve (Start Batch)", callback_data="prev_approve")],
            [InlineKeyboardButton("🔄 Regenerate AI Caption", callback_data="prev_regen")],
            [InlineKeyboardButton("✏️ Manual Edit", callback_data="prev_edit"),
             InlineKeyboardButton("⏭️ Skip AI", callback_data="prev_skip")]
        ])
        try:
            await query.message.edit_text(
                f"👀 **Smart Preview: AI Generated Caption**\n\n"
                f"Dekh lo bhai, naya AI caption kaisa lag raha hai:\n\n"
                f"<code>{preview_caption}</code>\n\n"
                f"👇 Action choose karo:",
                reply_markup=keyboard
            )
        except: pass 
        
    elif action == "prev_edit":
        Z[uid]['step'] = 'wait_for_manual_caption'
        await query.message.edit_text("📝 **Manual Edit Mode:**\n\nNeeche chat me apna custom caption type karke bhejo. Main usi ko poore batch me laga dunga.\n\n*(💡 Original file ka naam use karne ke liye `{filename}` likh sakte ho)*")

    elif action == "prev_skip":
        # AI ko skip karne ka flag set karo
        Z[uid]['task_data']['skip_ai'] = True
        
        # Database me bhi save kar do taaki crash hone pe yaad rahe
        from utils.func import db
        await db["tasks"].update_one({"user_id": uid}, {"$set": {"skip_ai": True}})
        
        await query.message.edit_text("⏭️ **AI Caption Skipped!**\n\n🚀 Original caption (with Replace/Remove rules) use hoga. Starting batch now...")
        await start_actual_batch(client, uid)