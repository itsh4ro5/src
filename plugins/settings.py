from telethon import events, Button
import re
import os
import string
import random
import requests
from pyrogram import filters
from pyrogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from shared_client import client as gf
from shared_client import app as X
from config import OWNER_ID

from utils.func import get_user_data_key, save_user_data, users_collection, is_premium_user

try:
    from theme_config import AVAILABLE_FONTS, AVAILABLE_COLORS, FONT_DIR
except ImportError:
    AVAILABLE_FONTS = {"default.ttf": "Standard Font"}
    AVAILABLE_COLORS = {"white": "⚪ White"}
    FONT_DIR = "fonts"

VIDEO_EXTENSIONS = {
    'mp4', 'mkv', 'avi', 'mov', 'wmv', 'flv', 'webm',
    'mpeg', 'mpg', '3gp'
}
SET_PIC = 'settings.jpg'
MESS = '⚙️ **Customize settings for your files...**\nSelect an option below to configure:'

active_conversations = {}

# 🟢 CANCEL KEYBOARDS
cancel_kb_telethon = [Button.text("❌ Cancel", resize=True, single_use=True)]
cancel_kb_pyro = ReplyKeyboardMarkup([[KeyboardButton("❌ Cancel")]], resize_keyboard=True, one_time_keyboard=True)


@gf.on(events.NewMessage(incoming=True, pattern='(?i)^/settings$'))
async def settings_command(event):
    user_id = event.sender_id
    await send_settings_message(event.chat_id, user_id)

# 🟢 DIRECT EXECUTION FROM HELP MENU
@gf.on(events.CallbackQuery(pattern=b"^run_settings$"))
async def direct_settings(event):
    await event.delete()
    await send_settings_message(event.chat_id, event.sender_id)

async def send_settings_message(chat_id, user_id):
    # 🟢 Fetch Current Direct Forward Status
    direct_forward = await get_user_data_key(user_id, 'direct_forward', False)
    df_status = "🟢 ON" if direct_forward else "🔴 OFF"

    buttons = [
        [
            Button.inline('📝 Set Chat ID', b'setchat'),
            Button.inline('🏷️ Set Rename Tag', b'setrename')
        ],
        [
            Button.inline('📋 Set Caption', b'setcaption'),
            Button.inline('🔄 Replace Words', b'setreplacement')
        ],
        [
            Button.inline('👤 Set Extractor Name', b'setextractor'),  
            Button.inline('🗑️ Remove Words', b'delete')
        ],
        [
            # 🔥 NAYA BUTTON YAHAN ADD HUA HAI 🔥
            Button.inline(f'⏩ Direct Forward: {df_status}', b'toggle_forward')
        ],
        [
            Button.inline('🔑 Session Login', b'addsession'),
            Button.inline('🚪 Logout', b'logout')
        ],
        [
            Button.inline('🎨 Thumbnail Fonts & Colors', b'thumb_settings')
        ],
        [
            Button.inline('🖼️ Set Thumbnail', b'setthumb'),
            Button.inline('❌ Remove Thumbnail', b'remthumb')
        ],
        [
            Button.inline('🔄 Reset Settings', b'reset')
        ],
        [
            Button.inline('◀️ Back to Help Menu', b'help_menu')
        ]
    ]
    await gf.send_message(chat_id, MESS, buttons=buttons)

async def render_thumb_settings(event, user_id):
    current_font = await get_user_data_key(user_id, "thumb_font", "default.ttf")
    current_color = await get_user_data_key(user_id, "thumb_color", "white")
    font_name = AVAILABLE_FONTS.get(current_font, "Standard Font")
    color_name = AVAILABLE_COLORS.get(current_color, "⚪ White")
    
    buttons = [
        [Button.inline('🔠 Change Font Style', b'menu_fonts_0')],
        [Button.inline('🖌 Change Font Color', b'menu_colors_0')],
        [Button.inline('🔙 Back to Settings', b'back_to_main')]
    ]
    await event.edit(f'🎨 **Thumbnail Customization**\n\n• Current Font: {font_name}\n• Current Color: {color_name}\n\nKya change karna chahte hain?', buttons=buttons)

@gf.on(events.CallbackQuery)
async def callback_query_handler(event):
    user_id = event.sender_id
    data_bytes = event.data
    data_str = data_bytes.decode('utf-8') if isinstance(data_bytes, bytes) else data_bytes
    
    callback_actions = {
        b'setchat': {
            'type': 'setchat',
            'message': "📝 **Send me the Chat ID** (with -100 prefix):\n__👉 Note: If you are using a custom bot, make sure your bot is an admin in that chat.__"
        },
        b'setrename': {
            'type': 'setrename',
            'message': '🏷️ **Send me the Rename Tag:**\n(Example: @YourChannelName)'
        },
        b'setcaption': {
            'type': 'setcaption',
            'message': '📋 **Send me the Caption:**\n(This will replace the entire original caption)'
        },
        b'setreplacement': {
            'type': 'setreplacement',
            'message': "🔄 **Send me the Replacement Words**\nFormat: `'OLD_WORD' 'NEW_WORD'`"
        },
        b'addsession': {
            'type': 'addsession',
            'message': '🔑 **Send Pyrogram V2 Session String:**'
        },
        b'setextractor': {
            'type': 'setextractor',
            'message': "👤 **Send me the Extractor Name:**\n(This name will be shown in AI generated captions)"
        },
        b'delete': {
            'type': 'deleteword',
            'message': '🗑️ **Send words to delete:**\n(Separate multiple words with a space)'
        },
        b'setthumb': {
            'type': 'setthumb',
            'message': '🖼️ **Set Thumbnail/Watermark:**\nPlease send the **Photo**, an **Image Link (URL)**, or type the **Text** you want to set.'
        }
    }
    
    if event.data in callback_actions:
        action = callback_actions[event.data]
        await start_conversation(event, user_id, action['type'], action['message'])
        
    # 🔥 ON/OFF TOGGLE LOGIC 🔥
    elif event.data == b'toggle_forward':
        current_state = await get_user_data_key(user_id, 'direct_forward', False)
        new_state = not current_state # True ko False, False ko True karega
        await save_user_data(user_id, 'direct_forward', new_state)
        await event.delete()
        await send_settings_message(event.chat_id, user_id)
        
    elif event.data == b'logout':
        result = await users_collection.update_one(
            {'user_id': user_id},
            {'$unset': {'session_string': ''}}
        )
        if result.modified_count > 0:
            await event.respond('✅ Logged out and deleted session successfully.')
        else:
            await event.respond('❌ You are not logged in.')
            
    elif event.data == b'reset':
        try:
            await users_collection.update_one(
                {'user_id': user_id},
                {'$unset': {
                    'delete_words': '',
                    'replacement_words': '',
                    'rename_tag': '',
                    'caption': '',
                    'chat_id': '',
                    'thumb_font': '',
                    'thumb_color': ''
                }}
            )
            thumbnail_path = f'{user_id}.jpg'
            if os.path.exists(thumbnail_path):
                os.remove(thumbnail_path)
            await event.respond('✅ All settings and thumbnails reset successfully.')
        except Exception as e:
            await event.respond(f'❌ Error resetting settings: {e}')
            
    elif event.data == b'remthumb':
        try:
            os.remove(f'{user_id}.jpg')
            await event.respond('✅ Thumbnail removed successfully!')
        except FileNotFoundError:
            await event.respond('❌ No thumbnail found to remove.')
            
    elif data_str == 'thumb_settings':
        await render_thumb_settings(event, user_id)
        
    elif data_str == 'back_to_main':
        await event.delete()
        await send_settings_message(event.chat_id, user_id)
        
    elif data_str.startswith('menu_fonts_'):
        page = int(data_str.split("_")[2])
        font_keys = list(AVAILABLE_FONTS.keys())
        per_page = 10
        start = page * per_page
        end = start + per_page
        current_fonts = font_keys[start:end]
        
        buttons = []
        for f_file in current_fonts:
            buttons.append([Button.inline(AVAILABLE_FONTS[f_file], f"set_font_{f_file}".encode('utf-8'))])
            
        nav_row = []
        if page > 0:
            nav_row.append(Button.inline("⬅️ Prev", f"menu_fonts_{page-1}".encode('utf-8')))
        if end < len(font_keys):
            nav_row.append(Button.inline("Next ➡️", f"menu_fonts_{page+1}".encode('utf-8')))
        
        if nav_row: buttons.append(nav_row)
        buttons.append([Button.inline("🔙 Back", b"thumb_settings")])
        
        await event.edit(f"🔠 **Select Font Style (Page {page+1}):**\n*(Upload files in {FONT_DIR}/ folder)*", buttons=buttons)
        
    elif data_str.startswith('menu_colors_'):
        page = int(data_str.split("_")[2])
        color_keys = list(AVAILABLE_COLORS.keys())
        per_page = 20
        start = page * per_page
        end = start + per_page
        current_colors = color_keys[start:end]
        
        buttons = []
        row = []
        for c_code in current_colors:
            row.append(Button.inline(AVAILABLE_COLORS[c_code], f"set_color_{c_code}".encode('utf-8')))
            if len(row) == 2:
                buttons.append(row)
                row = []
        if row: buttons.append(row)
        
        nav_row = []
        if page > 0:
            nav_row.append(Button.inline("⬅️ Prev", f"menu_colors_{page-1}".encode('utf-8')))
        if end < len(color_keys):
            nav_row.append(Button.inline("Next ➡️", f"menu_colors_{page+1}".encode('utf-8')))
            
        if nav_row: buttons.append(nav_row)
        buttons.append([Button.inline("🔙 Back", b"thumb_settings")])
        
        await event.edit(f"🖌 **Select Font Color (Page {page+1}):**", buttons=buttons)
        
    elif data_str.startswith('set_font_'):
        new_font = data_str.split("set_font_")[1]
        await save_user_data(user_id, "thumb_font", new_font)
        await event.answer(f"Font changed!", alert=True)
        await render_thumb_settings(event, user_id)
        
    elif data_str.startswith('set_color_'):
        new_color = data_str.split("set_color_")[1]
        await save_user_data(user_id, "thumb_color", new_color)
        await event.answer(f"Color changed!", alert=True)
        await render_thumb_settings(event, user_id)

async def start_conversation(event, user_id, conv_type, prompt_message):
    if user_id in active_conversations:
        await event.respond('⚠️ Previous operation cancelled. Starting new one.', buttons=Button.clear())
    
    # 🟢 ADDED CANCEL BUTTON TO ALL PROMPTS
    await event.respond(prompt_message, buttons=cancel_kb_telethon)
    active_conversations[user_id] = {'type': conv_type}

@gf.on(events.NewMessage())
async def handle_conversation_input(event):
    user_id = event.sender_id
    if user_id not in active_conversations:
        return
        
    # 🟢 CANCEL HANDLER
    if event.text in ['/cancel', '❌ Cancel']:
        await event.respond('🚫 **Operation Cancelled.**', buttons=Button.clear())
        del active_conversations[user_id]
        return
        
    if event.text and event.text.startswith('/'):
        return
        
    conv_type = active_conversations[user_id]['type']
    
    handlers = {
        'setchat': handle_setchat,
        'setrename': handle_setrename,
        'setcaption': handle_setcaption,
        'setreplacement': handle_setreplacement,
        'addsession': handle_addsession,
        'deleteword': handle_deleteword,
        'setthumb': handle_setthumb,
        'setextractor': handle_setextractor  
    }
    
    if conv_type in handlers:
        await handlers[conv_type](event, user_id)
    
    if user_id in active_conversations:
        del active_conversations[user_id]

# --- 💎 PREMIUM FEATURE: CUSTOM WATERMARK ---
@X.on_message(filters.command("setwm") & filters.private)
async def set_premium_watermark(c, m):
    uid = m.from_user.id
    
    if not await is_premium_user(uid):
        await m.reply_text("❌ **Premium Feature!**\nApna custom video watermark lagane ke liye Premium kharidein.")
        return
        
    if len(m.command) < 2:
        try:
            wm_msg = await c.ask(m.chat.id, "🖼️ **Please send the Watermark text you want to set:**", reply_markup=cancel_kb_pyro, timeout=120)
            if wm_msg.text in ["/cancel", "❌ Cancel"]: return await m.reply_text("🚫 **Cancelled.**", reply_markup=ReplyKeyboardRemove())
            watermark_text = wm_msg.text
        except Exception:
            return await m.reply_text("⏳ **Timeout! Operation cancelled.**", reply_markup=ReplyKeyboardRemove())
    else:
        watermark_text = m.text.split(None, 1)[1]
        
    await save_user_data(uid, "watermark", watermark_text)
    await m.reply_text(f"✅ **VIP Watermark Set!**\nAb aapki videos par `{watermark_text}` likh kar aayega.", reply_markup=ReplyKeyboardRemove())

@X.on_message(filters.command("remwm") & filters.private)
async def remove_premium_watermark(c, m):
    uid = m.from_user.id
    if not await is_premium_user(uid):
        await m.reply_text("❌ **Premium Feature!**")
        return
        
    await save_user_data(uid, "watermark", "")
    await m.reply_text("✅ Custom Watermark hata diya gaya hai.", reply_markup=ReplyKeyboardRemove())

# --- 💎 PREMIUM FEATURE: CUSTOM CAPTION FOOTER ---
@X.on_message(filters.command("setcap") & filters.private)
async def set_premium_caption(c, m):
    uid = m.from_user.id
    
    if not await is_premium_user(uid):
        await m.reply_text("❌ **Premium Feature!**")
        return
        
    if len(m.command) < 2:
        try:
            cap_msg = await c.ask(m.chat.id, "📝 **Please send the Custom Caption you want to set:**", reply_markup=cancel_kb_pyro, timeout=120)
            if cap_msg.text in ["/cancel", "❌ Cancel"]: return await m.reply_text("🚫 **Cancelled.**", reply_markup=ReplyKeyboardRemove())
            caption_text = cap_msg.text
        except Exception:
            return await m.reply_text("⏳ **Timeout! Operation cancelled.**", reply_markup=ReplyKeyboardRemove())
    else:
        caption_text = m.text.split(None, 1)[1]
        
    await save_user_data(uid, "caption", f"\n\n{caption_text}")
    await m.reply_text(f"✅ **VIP Caption Set!**\nAb har file ke neeche aapki branding aayegi.", reply_markup=ReplyKeyboardRemove())

async def handle_setchat(event, user_id):
    try:
        chat_id = event.text.strip()
        await save_user_data(user_id, 'chat_id', chat_id)
        await event.respond('✅ Chat ID set successfully!', buttons=Button.clear())
    except Exception as e:
        await event.respond(f'❌ Error setting chat ID: {e}', buttons=Button.clear())

async def handle_setrename(event, user_id):
    rename_tag = event.text.strip()
    await save_user_data(user_id, 'rename_tag', rename_tag)
    await event.respond(f'✅ Rename tag set to: {rename_tag}', buttons=Button.clear())

async def handle_setcaption(event, user_id):
    caption = event.text
    await save_user_data(user_id, 'caption', caption)
    await event.respond(f'✅ Caption set successfully!', buttons=Button.clear())

async def handle_setreplacement(event, user_id):
    match = re.match("'(.+)' '(.+)'", event.text)
    if not match:
        await event.respond("❌ Invalid format. Usage: 'WORD(s)' 'REPLACEWORD'", buttons=Button.clear())
    else:
        word, replace_word = match.groups()
        delete_words = await get_user_data_key(user_id, 'delete_words', [])
        if word in delete_words:
            await event.respond(f"❌ The word '{word}' is in the delete list and cannot be replaced.", buttons=Button.clear())
        else:
            replacements = await get_user_data_key(user_id, 'replacement_words', {})
            replacements[word] = replace_word
            await save_user_data(user_id, 'replacement_words', replacements)
            await event.respond(f"✅ Replacement saved: '{word}' will be replaced with '{replace_word}'", buttons=Button.clear())

async def handle_addsession(event, user_id):
    session_string = event.text.strip()
    await save_user_data(user_id, 'session_string', session_string)
    await event.respond('✅ Session string added successfully!', buttons=Button.clear())

async def handle_deleteword(event, user_id):
    words_to_delete = event.text.split()
    delete_words = await get_user_data_key(user_id, 'delete_words', [])
    delete_words = list(set(delete_words + words_to_delete))
    await save_user_data(user_id, 'delete_words', delete_words)
    await event.respond(f"✅ Words added to delete list: {', '.join(words_to_delete)}", buttons=Button.clear())

async def handle_setthumb(event, user_id):
    if event.photo:
        temp_path = await event.download_media()
        try:
            thumb_path = f'{user_id}.jpg'
            if os.path.exists(thumb_path):
                os.remove(thumb_path)
            os.rename(temp_path, thumb_path)
            await event.respond('✅ Thumbnail photo saved successfully!', buttons=Button.clear())
        except Exception as e:
            await event.respond(f'❌ Error saving thumbnail: {e}', buttons=Button.clear())
    elif event.text:
        text = event.text.strip()
        if text.startswith('http://') or text.startswith('https://'):
            status_msg = await event.respond('⏳ Downloading image from link...', buttons=Button.clear())
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                def download_img():
                    response = requests.get(text, timeout=10)
                    if response.status_code == 200:
                        with open(f'{user_id}.jpg', 'wb') as f:
                            f.write(response.content)
                        return True
                    return False
                
                success = await loop.run_in_executor(None, download_img)
                if success:
                    await status_msg.edit('✅ Thumbnail image downloaded and saved successfully!')
                else:
                    await status_msg.edit('❌ Failed to download image from the link.')
            except Exception as e:
                await status_msg.edit(f'❌ Error downloading image: {e}')
        else:
            await save_user_data(user_id, 'watermark', text)
            await event.respond(f'✅ Thumbnail text (Watermark) set to: {text}', buttons=Button.clear())
    else:
        await event.respond('❌ Please send a photo, an image link, or text. Operation cancelled.', buttons=Button.clear())

def generate_random_name(length=7):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

async def handle_setextractor(event, user_id):
    extractor_name = event.text.strip()
    await save_user_data(user_id, 'extractor_name', extractor_name)
    await event.respond(f'✅ Extractor Name set to: `{extractor_name}`\nAb AI generates captions me yahi naam aayega!', buttons=Button.clear())

# 🟢 CASE-INSENSITIVE FILE RENAMING
async def rename_file(file, sender, edit):
    try:
        delete_words = await get_user_data_key(sender, 'delete_words', [])
        custom_rename_tag = await get_user_data_key(sender, 'rename_tag', '')
        replacements = await get_user_data_key(sender, 'replacement_words', {})
        
        last_dot_index = str(file).rfind('.')
        if last_dot_index != -1 and last_dot_index != 0:
            ggn_ext = str(file)[last_dot_index + 1:]
            if ggn_ext.isalpha() and len(ggn_ext) <= 9:
                if ggn_ext.lower() in VIDEO_EXTENSIONS:
                    original_file_name = str(file)[:last_dot_index]
                    file_extension = 'mp4'
                else:
                    original_file_name = str(file)[:last_dot_index]
                    file_extension = ggn_ext
            else:
                original_file_name = str(file)[:last_dot_index]
                file_extension = 'mp4'
        else:
            original_file_name = str(file)
            file_extension = 'mp4'
        
        for word in delete_words:
            original_file_name = re.sub(re.escape(word), '', original_file_name, flags=re.IGNORECASE)
        
        for word, replace_word in replacements.items():
            original_file_name = re.sub(re.escape(word), replace_word, original_file_name, flags=re.IGNORECASE)
        
        new_file_name = f'{original_file_name} {custom_rename_tag}.{file_extension}'
        new_file_name = re.sub(r'\s+', ' ', new_file_name).strip()
        
        os.rename(file, new_file_name)
        return new_file_name
    except Exception as e:
        print(f"Rename error: {e}")
        return file