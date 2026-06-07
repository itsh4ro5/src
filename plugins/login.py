from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import BadRequest, SessionPasswordNeeded, PhoneCodeInvalid, PhoneCodeExpired, MessageNotModified
import logging
import os
import random
import asyncio
from pyrogram import ContinuePropagation
from shared_client import app
from config import API_HASH, API_ID
from shared_client import app as bot
from utils.func import save_user_session, get_user_data, remove_user_session, save_user_bot, remove_user_bot
from utils.encrypt import ecs, dcs
from plugins.batch import UB, UC
from utils.custom_filters import login_in_progress, set_user_step, get_user_step

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Aapke main.py wala exact device spoofing parameters
DEVICE_MODELS = [
    "realme P3 Pro 5G", "Samsung Galaxy S23 Ultra", "OnePlus 11R", 
    "Xiaomi 13 Pro", "Google Pixel 8 Pro", "Vivo X90 Pro"
]
SYSTEM_VERSION = "Android 14"
APP_VERSION = "12.5.2"

STEP_PHONE = 1
STEP_CODE = 2
STEP_PASSWORD = 3
login_cache = {}

@bot.on_message(filters.command('login'))
async def login_command(client, message):
    user_id = message.from_user.id
    set_user_step(user_id, STEP_PHONE)
    login_cache.pop(user_id, None)
    await message.delete()
    status_msg = await message.reply(
        """Please send your phone number with country code
Example: `+916205730972`"""
        )
    login_cache[user_id] = {'status_msg': status_msg}
    
    
@bot.on_message(filters.command("setbot"))
async def set_bot_token(C, m):
    user_id = m.from_user.id
    args = m.text.split(" ", 1)
    if user_id in UB:
        try:
            await UB[user_id].stop()
            if UB.get(user_id, None):
                del UB[user_id] 
                
            try:
                if os.path.exists(f"user_{user_id}.session"):
                    os.remove(f"user_{user_id}.session")
            except Exception:
                pass
            
            print(f"Stopped and removed old bot for user {user_id}")
        except Exception as e:
            print(f"Error stopping old bot for user {user_id}: {e}")
            del UB[user_id] 

    if len(args) < 2:
        await m.reply_text("⚠️ Please provide a bot token. Usage: `/setbot token`", quote=True)
        return

    bot_token = args[1].strip()
    await save_user_bot(user_id, bot_token)
    await m.reply_text("✅ Bot token saved successfully.", quote=True)
    
    
@bot.on_message(filters.command("rembot"))
async def rem_bot_token(C, m):
    user_id = m.from_user.id
    if user_id in UB:
        try:
            await UB[user_id].stop()
            
            if UB.get(user_id, None):
                del UB[user_id] 
            print(f"Stopped and removed old bot for user {user_id}")
            try:
                if os.path.exists(f"user_{user_id}.session"):
                    os.remove(f"user_{user_id}.session")
            except Exception:
                pass
        except Exception as e:
            print(f"Error stopping old bot for user {user_id}: {e}")
            if UB.get(user_id, None):
                del UB[user_id] 
            try:
                if os.path.exists(f"user_{user_id}.session"):
                    os.remove(f"user_{user_id}.session")
            except Exception:
                pass
    await remove_user_bot(user_id)
    await m.reply_text("✅ Bot token removed successfully.", quote=True)

    
@bot.on_message(login_in_progress & filters.text & filters.private & ~filters.command([
    'start', 'batch', 'cancel', 'login', 'logout', 'stop', 'set', 'pay',
    'redeem', 'gencode', 'generate', 'keyinfo', 'encrypt', 'decrypt', 'keys', 'setbot', 'rembot']))
async def handle_login_steps(client, message):
    user_id = message.from_user.id
    text = message.text.strip()
    step = get_user_step(user_id)
    try:
        await message.delete()
    except Exception as e:
        logger.warning(f'Could not delete message: {e}')
    status_msg = login_cache[user_id].get('status_msg')
    if not status_msg:
        status_msg = await message.reply('Processing...')
        login_cache[user_id]['status_msg'] = status_msg
    try:
        if step == STEP_PHONE:
            if not text.startswith('+'):
                await edit_message_safely(status_msg,
                    '❌ Please provide a valid phone number starting with +')
                return
            await edit_message_safely(status_msg,
                '🔄 Processing phone number...')
            
            # AAPKE MAIN.PY WALA METHOD YAHAN ADD KIYA GAYA HAI
            temp_client = Client(
                f'temp_{user_id}', 
                api_id=API_ID, 
                api_hash=API_HASH, 
                in_memory=True,
                device_model=random.choice(DEVICE_MODELS), # <--- Dynamic
                system_version="Android 14",
                app_version="12.5.2",
                sleep_threshold=120
            )
            
            try:
                await temp_client.connect()
                
                # Human behavior delay
                await asyncio.sleep(random.uniform(2.3, 4.8)) 
                
                sent_code = await temp_client.send_code(text)
                login_cache[user_id]['phone'] = text
                login_cache[user_id]['phone_code_hash'
                    ] = sent_code.phone_code_hash
                login_cache[user_id]['temp_client'] = temp_client
                set_user_step(user_id, STEP_CODE)
                await edit_message_safely(status_msg,
                    """✅ Verification code sent to your Telegram account.
                    
Please enter the code you received like 1 2 3 4 5 (i.e seperated by space):"""
                    )
            except BadRequest as e:
                await edit_message_safely(status_msg,
                    f"""❌ Error: {str(e)}
Please try again with /login.""")
                await temp_client.disconnect()
                set_user_step(user_id, None)
                
        elif step == STEP_CODE:
            code = text.replace(' ', '')
            phone = login_cache[user_id]['phone']
            phone_code_hash = login_cache[user_id]['phone_code_hash']
            temp_client = login_cache[user_id]['temp_client']
            try:
                await edit_message_safely(status_msg, '🔄 Verifying code...')
                
                await asyncio.sleep(random.uniform(3.1, 5.7))
                
                await temp_client.sign_in(phone, phone_code_hash, code)
                session_string = await temp_client.export_session_string()
                encrypted_session = ecs(session_string)
                await save_user_session(user_id, encrypted_session)
                await temp_client.disconnect()
                temp_status_msg = login_cache[user_id]['status_msg']
                login_cache.pop(user_id, None)
                login_cache[user_id] = {'status_msg': temp_status_msg}
                await edit_message_safely(status_msg,
                    """✅ Logged in successfully!!"""
                    )
                set_user_step(user_id, None)
            except SessionPasswordNeeded:
                set_user_step(user_id, STEP_PASSWORD)
                await edit_message_safely(status_msg,
                    """🔒 Two-step verification is enabled.
Please enter your password:"""
                    )
            except (PhoneCodeInvalid, PhoneCodeExpired) as e:
                await edit_message_safely(status_msg,
                    f'❌ {str(e)}. Please try again with /login.')
                await temp_client.disconnect()
                login_cache.pop(user_id, None)
                set_user_step(user_id, None)
                
        elif step == STEP_PASSWORD:
            temp_client = login_cache[user_id]['temp_client']
            try:
                await edit_message_safely(status_msg, '🔄 Verifying password...'
                    )
                    
                await asyncio.sleep(random.uniform(2.5, 4.2))
                
                await temp_client.check_password(text)
                session_string = await temp_client.export_session_string()
                encrypted_session = ecs(session_string)
                await save_user_session(user_id, encrypted_session)
                await temp_client.disconnect()
                temp_status_msg = login_cache[user_id]['status_msg']
                login_cache.pop(user_id, None)
                login_cache[user_id] = {'status_msg': temp_status_msg}
                await edit_message_safely(status_msg,
                    """✅ Logged in successfully!!"""
                    )
                set_user_step(user_id, None)
            except BadRequest as e:
                await edit_message_safely(status_msg,
                    f"""❌ Incorrect password: {str(e)}
Please try again:""")
    except Exception as e:
        logger.error(f'Error in login flow: {str(e)}')
        await edit_message_safely(status_msg,
            f"""❌ An error occurred: {str(e)}
Please try again with /login.""")
        if user_id in login_cache and 'temp_client' in login_cache[user_id]:
            await login_cache[user_id]['temp_client'].disconnect()
        login_cache.pop(user_id, None)
        set_user_step(user_id, None)

async def edit_message_safely(message, text):
    """Helper function to edit message and handle errors"""
    try:
        await message.edit(text)
    except MessageNotModified:
        pass
    except Exception as e:
        logger.error(f'Error editing message: {e}')
        
@bot.on_message(filters.command('cancel'))
async def cancel_command(client, message):
    user_id = message.from_user.id
    
    # Check karo ki kya sach me koi login process chal raha hai?
    if get_user_step(user_id):
        await message.delete()
        status_msg = login_cache.get(user_id, {}).get('status_msg')
        if user_id in login_cache and 'temp_client' in login_cache[user_id]:
            await login_cache[user_id]['temp_client'].disconnect()
        login_cache.pop(user_id, None)
        set_user_step(user_id, None)
        if status_msg:
            await edit_message_safely(status_msg, '✅ Login process cancelled. Use /login to start again.')
        else:
            temp_msg = await message.reply('✅ Login process cancelled. Use /login to start again.')
            await temp_msg.delete(5)
            
    else:
        # 🔥 FIX: Agar login nahi chal raha, toh Error dene ke bajaye aage `batch.py` ya `arrange.py` ko command handle karne do
        raise ContinuePropagation
        
@bot.on_message(filters.command('logout'))
async def logout_command(client, message):
    user_id = message.from_user.id
    await message.delete()
    status_msg = await message.reply('🔄 Processing logout request...')
    try:
        session_data = await get_user_data(user_id)
        
        if not session_data or 'session_string' not in session_data:
            await edit_message_safely(status_msg,
                '❌ No active session found for your account.')
            return
        encss = session_data['session_string']
        session_string = dcs(encss)
        
        # 🟢 YAHAN FIX KIYA GAYA HAI (random.choice(DEVICE_MODELS) lagaya hai)
        temp_client = Client(
            f'temp_logout_{user_id}', 
            api_id=API_ID,
            api_hash=API_HASH, 
            session_string=session_string,
            device_model=random.choice(DEVICE_MODELS), 
            system_version=SYSTEM_VERSION,
            app_version=APP_VERSION
        )
        
        try:
            await temp_client.connect()
            await temp_client.log_out()
            await edit_message_safely(status_msg,
                '✅ Telegram session terminated successfully. Removing from database...'
                )
        except Exception as e:
            logger.error(f'Error terminating session: {str(e)}')
            await edit_message_safely(status_msg,
                f"""⚠️ Error terminating Telegram session: {str(e)}
Still removing from database..."""
                )
        finally:
            await temp_client.disconnect()
            
        await remove_user_session(user_id)
        await edit_message_safely(status_msg,
            '✅ Logged out successfully!!')
            
        try:
            if os.path.exists(f"{user_id}_client.session"):
                os.remove(f"{user_id}_client.session")
        except Exception:
            pass
        if UC.get(user_id, None):
            del UC[user_id]
            
    except Exception as e:
        logger.error(f'Error in logout command: {str(e)}')
        try:
            await remove_user_session(user_id)
        except Exception:
            pass
        if UC.get(user_id, None):
            del UC[user_id]
        await edit_message_safely(status_msg,
            f'❌ An error occurred during logout: {str(e)}')
        try:
            if os.path.exists(f"{user_id}_client.session"):
                os.remove(f"{user_id}_client.session")
        except Exception:
            pass

@app.on_callback_query(filters.regex("^(run_login|run_logout|run_setbot|run_rembot)$"))
async def direct_login_actions(c, q):
    cmd = q.data.replace("run_", "")
    await q.message.delete()
    
    # Posing as user message
    q.message.text = f"/{cmd}"
    q.message.from_user = q.from_user
    
    if cmd == "login": 
        await login_command(c, q.message)
    elif cmd == "logout": 
        await logout_command(c, q.message)
    elif cmd == "setbot": 
        await set_bot_token(c, q.message)  # <--- Yaha fix kiya
    elif cmd == "rembot": 
        await rem_bot_token(c, q.message)  # <--- Yaha fix kiya