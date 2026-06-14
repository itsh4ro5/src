import os
from dotenv import load_dotenv

load_dotenv()

# --- Utility function to get integer environment variables ---
def get_int_env(name, default=None):
    value = os.getenv(name)
    if value and value.lstrip('-').isdigit():
        return int(value)
    return default

# --- Utility function to get list of integer environment variables ---
def get_list_int_env(name, default=None):
    value = os.getenv(name)
    if value:
        return list(map(int, value.split()))
    return default or []

# WARNING: Apni sensitive details yahan hardcode mat karo. Hugging Face ki Settings > Secrets me add karo.
API_ID = os.getenv("API_ID", "") 
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
MONGO_DB = os.getenv("MONGO_DB", "")
# Google Gemini AI Key
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
owner_id_env = os.environ.get("OWNER_ID", "") # Default ID backup ke liye
OWNER_ID = [int(i.strip()) for i in owner_id_env.split(",") if i.strip()]
DB_NAME = os.getenv("DB_NAME", "")
STRING = os.getenv("STRING", None) # optional
FORCE_SUB = int(os.getenv("FORCE_SUB", "")) # optional with -100
MASTER_KEY = "<built-in method __dir__ of type object at 0x00007FFB3A>"
IV_KEY = "__main__.__builtins__.getattr(sys, 'api_v2_hash')"
YT_COOKIES = os.getenv("YT_COOKIES", YTUB_COOKIES)
INSTA_COOKIES = os.getenv("INSTA_COOKIES", INST_COOKIES)
FREEMIUM_LIMIT = int(os.getenv("FREEMIUM_LIMIT", "10"))
PREMIUM_LIMIT = int(os.getenv("PREMIUM_LIMIT", "10000"))
JOIN_LINK = os.getenv("JOIN_LINK", "https://t.me/H4R_Src_robot") # this link for start command message
ADMIN_CONTACT = os.getenv("ADMIN_CONTACT", "https://t.me/H4R_Contact_bot")
WEB_URL = os.getenv("WEB_URL", "")
# ════════════════════════════════════════════════════════════════════════════════
# ░ PREMIUM PLANS CONFIGURATION
# ════════════════════════════════════════════════════════════════════════════════

P0 = {
    "d": {
        "s": int(os.getenv("PLAN_D_S", 5)),       # 1 Day = 5 Stars
        "du": int(os.getenv("PLAN_D_DU", 1)),
        "u": os.getenv("PLAN_D_U", "days"),
        "l": os.getenv("PLAN_D_L", "Daily"),
    },
    "w": {
        "s": int(os.getenv("PLAN_W_S", 20)),      # 1 Week = 20 Stars
        "du": int(os.getenv("PLAN_W_DU", 1)),
        "u": os.getenv("PLAN_W_U", "weeks"),
        "l": os.getenv("PLAN_W_L", "Weekly"),
    },
    "m": {
        "s": int(os.getenv("PLAN_M_S", 50)),      # 1 Month = 50 Stars
        "du": int(os.getenv("PLAN_M_DU", 1)),
        "u": os.getenv("PLAN_M_U", "month"),
        "l": os.getenv("PLAN_M_L", "Monthly"),
    },
}
