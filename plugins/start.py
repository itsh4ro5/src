import base64
import traceback
from datetime import datetime
from shared_client import app
from pyrogram import filters
from pyrogram.errors import UserNotParticipant
from pyrogram.types import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from config import OWNER_ID, FORCE_SUB

from utils.db import check_and_add_referral, check_referral_reward, users_collection, premium_collection
from utils.func import a7, a8, a9, a10, a11, get_user_data_key

refer_enc = "Cgrwn4yRICAqKldhbnQgRnJlZSBQcmVtaXVtPyoqClVzZSAvcmVmZXIgY29tbWFuZCB0byBpbnZpdGUgeW91ciBmcmllbmRzIGFuZCBnZXQgYSAxLURheSBWSVAgUGxhbiBhYnNvbHV0ZWx5IEZSRUUh"

tc_text = (
    "📜 **Terms & Conditions** 📜\n\n"
    "1. We do not promote or endorse any copyrighted content or illegal activities.\n"
    "2. The bot owner holds no responsibility if your channel, group, or account gets banned.\n"
    "3. Any misuse of the bot will result in a penalty and a permanent ban from our services.\n"
    "4. The bot owner is not liable for any damages, misuse, or legal consequences arising from the use of this bot.\n\n"
    "Do you accept these terms?"
)

async def is_member(user_id):
    if not FORCE_SUB: return True
    try:
        user = await app.get_chat_member(FORCE_SUB, user_id)
        if str(user.status) in ["ChatMemberStatus.OWNER", "ChatMemberStatus.ADMINISTRATOR", "ChatMemberStatus.MEMBER"]:
            return True
    except UserNotParticipant: return False
    except Exception: return True
    return False

async def check_is_prem(user_id):
    if user_id in OWNER_ID: return True
    prem_user = await premium_collection.find_one({"user_id": user_id})
    if prem_user and prem_user.get("subscription_end") and prem_user.get("subscription_end") > datetime.now():
        return True
    return False

@app.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message):
    user_id = message.from_user.id
    
    # 🟢 NEW CODE: Har baar start hone par user ka Asli Naam DB me save karo
    try:
        await users_collection.update_one(
            {"_id": user_id},
            {"$set": {
                "first_name": message.from_user.first_name or "User",
                "username": message.from_user.username or "None"
            }},
            upsert=True
        )
    except Exception as e:
        print(f"Error saving user name: {e}")
        pass
    
    if len(message.command) > 1 and message.command[1].startswith("ref_"):
        try:
            ref_id = int(message.command[1].split("_")[1])
            if await check_and_add_referral(user_id, ref_id):
                if await check_referral_reward(ref_id):
                    await client.send_message(ref_id, "🎉 **CONGRATULATIONS!** 1 Day VIP mil gaya. 👑")
                else:
                    await client.send_message(ref_id, "🔔 **New Referral!** Ek dost ne join kiya hai.")
        except: pass

    if not await is_member(user_id):
        try: link = await app.export_chat_invite_link(FORCE_SUB)
        except: link = "https://t.me/H4R_Src_robot"
        markup = InlineKeyboardMarkup([[InlineKeyboardButton("📢 Join Channel", url=link)], [InlineKeyboardButton("✅ Verify Subscribe", callback_data="verify_sub")]])
        await message.reply_photo(photo="https://i.ibb.co/qLSbQYGP/x.jpg", caption="⚠️ **Access Denied!**\nBot use karne ke liye pehle channel join karein.", reply_markup=markup)
        return

    user_data = await users_collection.find_one({"_id": user_id})
    if not user_data or not user_data.get("tc_accepted"):
        markup = InlineKeyboardMarkup([[InlineKeyboardButton("✅ I Accept", callback_data="accept_tc")], [InlineKeyboardButton("❌ Decline", callback_data="decline_tc")]])
        await message.reply_text(tc_text, reply_markup=markup)
        return

    await show_welcome(message)

async def show_welcome(message_or_query):
    welcome = base64.b64decode(a7).decode('utf-8')
    b1, b2 = base64.b64decode(a8).decode('utf-8'), base64.b64decode(a9).decode('utf-8')
    u1, u2 = base64.b64decode(a10).decode('utf-8'), base64.b64decode(a11).decode('utf-8')
    ref_hint = base64.b64decode(refer_enc).decode('utf-8')

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton(b1, url=u1), InlineKeyboardButton(b2, url=u2)],
        [InlineKeyboardButton("💰 Plans", callback_data="see_plan"), InlineKeyboardButton("🗂️ Help & Commands", callback_data="help_menu")]
    ])
    
    caption = f"{welcome}\n\n{ref_hint}"
    if isinstance(message_or_query, CallbackQuery):
        await message_or_query.message.delete()
        await message_or_query.message.reply_photo(photo="https://i.ibb.co/qLSbQYGP/x.jpg", caption=caption, reply_markup=markup)
    else:
        await message_or_query.reply_photo(photo="https://i.ibb.co/qLSbQYGP/x.jpg", caption=caption, reply_markup=markup)

COMMAND_LABELS = {
    "start": "🚀 Start", "help": "❓ Help", "id": "🆔 ID", "plan": "💰 Plan",
    "refer": "🎁 Refer", "login": "🔑 Login", "logout": "🚪 Logout", 
    "setbot": "🧸 Setbot", "rembot": "🤨 Rembot", "batch": "🫠 Batch",
    "docbatch": "📄 DocBatch",
    "single": "🔗 Single", "cancel": "🚫 Cancel", "redeem": "🎟 Redeem Code", "fix": "🛠 Fix",
    "settings": "🎨 Settings", "autosync": "🔄 AutoSync", "delsync": "🛑 DelSync", 
    "setcookie": "🍪 Cookie", "pay": "💎 Pay", 
    "status": "📊 Status", "admin": "👑 Admin Panel",
    "arrange": "📦 Arrange" 
}

FREE_COMMANDS = ["id", "plan", "refer", "login", "logout", "setbot", "rembot", "batch", "docbatch", "cancel", "pay", "status", "redeem"] 
PREMIUM_COMMANDS = ["settings", "setcookie", "single", "autosync", "delsync", "arrange"]
OWNER_COMMANDS = ["admin", "set", "fix"]

def get_help_keyboard(category):
    buttons = []
    row = []
    
    if category == "free": cmds = FREE_COMMANDS
    elif category == "premium": cmds = FREE_COMMANDS + PREMIUM_COMMANDS
    elif category == "owner": cmds = FREE_COMMANDS + PREMIUM_COMMANDS + OWNER_COMMANDS
        
    for cmd in cmds:
        label = COMMAND_LABELS.get(cmd, cmd)
        if cmd == "plan": cb_data = "see_plan"
        elif cmd == "refer": cb_data = "see_refer"
        elif cmd == "pay": cb_data = "direct_pay"
        elif cmd == "id": cb_data = "see_id"
        else: cb_data = f"run_{cmd}"
        
        row.append(InlineKeyboardButton(label, callback_data=cb_data))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row: buttons.append(row)
    
    # 🟢 TEASER BUTTON IN FREE MENU
    if category == "free":
        buttons.append([InlineKeyboardButton("✨ What's in Premium?", callback_data="premium_teaser")])
        
    buttons.append([InlineKeyboardButton("◀️ Back to Categories", callback_data="help_menu")])
    buttons.append([InlineKeyboardButton("🏠 Home", callback_data="go_home")])
    return InlineKeyboardMarkup(buttons)

@app.on_callback_query(filters.regex(r"^(verify_sub|accept_tc|decline_tc|help_menu|help_cat_free|help_cat_prem|help_cat_owner|go_home|see_plan|see_terms|see_refer|see_id|direct_pay|premium_teaser)$"))
async def handle_callbacks(client, query):
    user_id = query.from_user.id
    data = query.data
    
    if data == "verify_sub":
        if await is_member(user_id):
            await query.answer("✅ Subscribed Successfully!", show_alert=True)
            user_data = await users_collection.find_one({"_id": user_id})
            if not user_data or not user_data.get("tc_accepted"):
                markup = InlineKeyboardMarkup([[InlineKeyboardButton("✅ I Accept", callback_data="accept_tc")], [InlineKeyboardButton("❌ Decline", callback_data="decline_tc")]])
                await query.message.edit_text(tc_text, reply_markup=markup)
            else:
                await show_welcome(query)
        else:
            await query.answer("❌ Abhi tak join nahi kiya hai!", show_alert=True)

    elif data == "accept_tc":
        await users_collection.update_one({"_id": user_id}, {"$set": {"tc_accepted": True}}, upsert=True)
        await query.answer("✅ Terms Accepted!", show_alert=True)
        await show_welcome(query)

    elif data == "decline_tc":
        await query.answer("❌ Jab tak accept nahi karenge, bot kaam nahi karega.", show_alert=True)

    elif data == "help_menu":
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🟢 Free Features", callback_data="help_cat_free")],
            [InlineKeyboardButton("💎 Premium Features", callback_data="help_cat_prem")],
            [InlineKeyboardButton("👑 Owner Features", callback_data="help_cat_owner")],
            [InlineKeyboardButton("🏠 Home", callback_data="go_home")]
        ])
        await query.message.edit_text("🗂 **Help & Commands Menu**\n\nSelect a category below to view available commands:", reply_markup=markup)

    elif data == "help_cat_free":
        await query.message.edit_text("🟢 **Free Features**\nSelect a command directly to execute:", reply_markup=get_help_keyboard("free"))
        
    elif data == "premium_teaser":
        # 🟢 PREMIUM SNEAK PEEK
        teaser = (
            "💎 **Unlock the True Power of H4R SRC!** 💎\n\n"
            "Premium users enjoy exclusive, advanced features to supercharge their experience:\n\n"
            "🎨 **Custom Watermarks:** Add your unique branding on videos.\n"
            "📝 **Custom Footers:** Automatically attach your links below captions.\n"
            "💀 **Smart Downloader:** Download media directly from YouTube & Instagram.\n"
            "🔄 **AutoSync:** Keep your source & target channels synchronized 24/7.\n"
            "🔗 **Single Link:** Extract a single file perfectly without limits.\n"
            "🚀 **Massive Bulk:** Extract up to **100,000 files** in a single batch!\n\n"
            "Take your extraction game to the next level today! 👇"
        )
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🛒 Upgrade to VIP", callback_data="direct_pay")],
            [InlineKeyboardButton("◀️ Back to Free Features", callback_data="help_cat_free")]
        ])
        await query.message.edit_text(teaser, reply_markup=markup)

    elif data == "help_cat_prem":
        if not await check_is_prem(user_id):
            locked_text = "❌ **Premium Features Locked!**\n\nTo access the premium commands, please buy our services.\nUnlock all powerful VIP features today! 🚀"
            markup = InlineKeyboardMarkup([[InlineKeyboardButton("🛒 Buy Premium", callback_data="see_plan")], [InlineKeyboardButton("◀️ Back", callback_data="help_menu")]])
            return await query.message.edit_text(locked_text, reply_markup=markup)
        await query.message.edit_text("💎 **Premium Features**\nSelect a command directly to execute:", reply_markup=get_help_keyboard("premium"))

    elif data == "help_cat_owner":
        if user_id not in OWNER_ID:
            return await query.answer("❌ Access Denied! Only the Bot Owner can view these features.", show_alert=True)
        await query.message.edit_text("👑 **Owner Features**\nSelect a command directly to execute:", reply_markup=get_help_keyboard("owner"))

    elif data == "go_home":
        await show_welcome(query)

    elif data == "see_plan":
        plan_text = "> 💰 **Premium Price (Telegram Stars ⭐)**:\n\n🌟 **1 Day Plan:** 5 Stars\n🌟 **Weekly Plan:** 20 Stars\n🌟 **Monthly Plan:** 50 Stars\n\n📥 **Download Limit**: Users can download up to 100,000 files in a single batch command."
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🛒 Buy Now", callback_data="direct_pay")], 
            [InlineKeyboardButton("◀️ Back", callback_data="help_menu")]
        ])
        await query.message.edit_text(plan_text, reply_markup=markup)

    elif data == "direct_pay":
        pay_info = (
            "💎 **Purchase Premium** 💎\n\n"
            "💳 **UPI ID:** `your-upi@ybl`\n"
            "🏦 **Binance Pay ID:** `12345678`\n\n"
            "📝 *Note:* Payment karne ke baad screenshot apne User ID ke sath Admin ko send karein. Admin aapka plan activate kar dega!"
        )
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("👨‍💻 Send Screenshot to Admin", url="https://t.me/H4R_Contact_bot")],
            [InlineKeyboardButton("◀️ Back to Plans", callback_data="see_plan")]
        ])
        await query.message.edit_text(pay_info, reply_markup=markup)

    elif data == "see_terms":
        markup = InlineKeyboardMarkup([[InlineKeyboardButton("📋 See Plans", callback_data="see_plan")], [InlineKeyboardButton("◀️ Back", callback_data="help_menu")]])
        await query.message.edit_text(tc_text, reply_markup=markup)
            
    elif data == "see_id":
        text = f"🆔 **Current Chat ID:** `{query.message.chat.id}`\n"
        markup = InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Back", callback_data="help_menu")]])
        await query.message.edit_text(text, reply_markup=markup)

    elif data == "run_redeem":
        redeem_info = "🎟 **Redeem Premium Code**\n\nAgar aapke paas premium code hai, toh usko is format me bhejein:\n\n👉 `/redeem <aapka_code>`\n\nExample: `/redeem ABC123XYZ`"
        markup = InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Back to Free Features", callback_data="help_cat_free")]])
        await query.message.edit_text(redeem_info, reply_markup=markup)

# 🟢 BOT MENU UPDATE (ONLY FREE COMMANDS)
@app.on_message(filters.command("set"))
async def set(_, message):
    if message.from_user.id not in OWNER_ID: return
    await app.set_bot_commands([
        BotCommand("start", "🚀 Start the bot"), 
        BotCommand("batch", "🫠 Extract in bulk"),
        BotCommand("docbatch", "📄 Extract PDFs & Images only"),
        BotCommand("login", "🔑 Get into the bot"), 
        BotCommand("logout", "🚪 Logout from bot"),
        BotCommand("setbot", "🧸 Add Userbot token"),
        BotCommand("rembot", "🤨 Remove Userbot token"),
        BotCommand("status", "📊 Check Subscription"),
        BotCommand("plan", "💰 View Plans"),
        BotCommand("pay", "💎 Buy Premium"),
        BotCommand("cancel", "🚫 Cancel Process")
    ])
    await message.reply("✅ Bot Commands Menu configured successfully!\n(Only Free commands are now visible in the Blue Menu)")

async def subscribe(client, message):
    user_id = message.from_user.id
    if not await is_member(user_id):
        try: link = await app.export_chat_invite_link(FORCE_SUB)
        except Exception: link = "https://t.me/H4R_Src_robot"
        markup = InlineKeyboardMarkup([[InlineKeyboardButton("📢 Join Channel", url=link)], [InlineKeyboardButton("✅ Verify Subscribe", callback_data="verify_sub")]])
        await message.reply_photo(photo="https://i.ibb.co/qLSbQYGP/x.jpg", caption="⚠️ **Access Denied!**\nYou must join our channel to use this command.", reply_markup=markup)
        return 1 
    return 0

@app.on_callback_query(filters.regex("^run_status$"))
async def status_callback(client, query):
    user_id = query.from_user.id
    
    # Database se user ki details fetch karein
    session_str = await get_user_data_key(user_id, "session_string", None)
    bot_token = await get_user_data_key(user_id, "bot_token", None)
    is_prem = await check_is_prem(user_id)
    
    status_text = (
        "📊 **Aapka Live Account Status** 📊\n\n"
        f"🔑 **Session Login Status:** {'✅ Logged In' if session_str else '❌ Not Logged In'}\n"
        f"🧸 **Custom Bot Status:** {'✅ Configured / Set' if bot_token else '❌ Not Set'}\n"
        f"💎 **Subscription Plan:** {'👑 Premium VIP User' if is_prem else '🟢 Free User'}\n\n"
        "👉 Agar aapko session login ya bot token set/change karna hai, toh `/settings` command ka use karein."
    )
    
    # Back button lagaya hai taaki user wapas Help Menu me ja sake
    markup = InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Back ke liye click karein", callback_data="help_menu")]])
    await query.message.edit_text(status_text, reply_markup=markup)
    
@app.on_message(filters.command("status") & filters.private)
async def status_cmd(client, message):
    user_id = message.from_user.id
    
    # Database se user ki details fetch karein
    session_str = await get_user_data_key(user_id, "session_string", None)
    bot_token = await get_user_data_key(user_id, "bot_token", None)
    is_prem = await check_is_prem(user_id)
    
    status_text = (
        "📊 **Aapka Account Status** 📊\n\n"
        f"🔑 **Session Login Status:** {'✅ Logged In' if session_str else '❌ Not Logged In'}\n"
        f"🧸 **Custom Bot Status:** {'✅ Configured / Set' if bot_token else '❌ Not Set'}\n"
        f"💎 **Subscription Plan:** {'👑 Premium VIP User' if is_prem else '🟢 Free User'}\n\n"
        "👉 Kuch bhi change karne ke liye `/settings` ka use karein."
    )
    await message.reply_text(status_text)
