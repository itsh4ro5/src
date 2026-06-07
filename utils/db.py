from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_DB, DB_NAME
from datetime import datetime, timedelta

# 🟢 1. Database Connection Setup
client = AsyncIOMotorClient(MONGO_DB)
db = client[DB_NAME]

# Collections
users_collection = db["users"]             # Normal users ke liye
premium_collection = db["premium_users"]   # Premium/VIP users ke liye

# ======================================================================
# 🍪 COOKIE MANAGEMENT SYSTEM (For YT/Insta Downloads)
# ======================================================================

async def save_user_cookie(user_id, platform, cookie_text):
    """User ke specific platform (YT/Insta) ki cookies save karta hai"""
    await users_collection.update_one(
        {"_id": user_id},
        {"$set": {f"cookies.{platform}": cookie_text}},
        upsert=True
    )

async def get_user_cookie(user_id, platform):
    """User ki saved cookies fetch karta hai"""
    user = await users_collection.find_one({"_id": user_id})
    if user and "cookies" in user and platform in user["cookies"]:
        return user["cookies"][platform]
    return None


# ======================================================================
# 🚀 REFERRAL & REWARD SYSTEM (Market Dominator Feature)
# ======================================================================

async def check_and_add_referral(new_user_id, referrer_id):
    """
    Check karega ki naya user valid hai ya nahi, aur refer count badhayega.
    Fake refer (khud ko refer karna ya old user ko refer karna) block karega.
    """
    # 1. Khud ko refer karna allow nahi hai
    if int(new_user_id) == int(referrer_id):
        return False 
        
    # 2. Check agar user pehle se DB me maujood hai (Old User)
    existing_user = await users_collection.find_one({"_id": new_user_id})
    if existing_user:
        return False # Count nahi badhega kyunki user naya nahi hai
        
    # 3. Naye user ko DB me entry do
    await users_collection.insert_one({
        "_id": new_user_id,
        "referred_by": referrer_id,
        "join_date": datetime.now()
    })
    
    # 4. Jisne refer kiya (referrer) uska count +1 kar do
    await users_collection.update_one(
        {"_id": referrer_id},
        {"$inc": {"referral_count": 1}},
        upsert=True
    )
    return True

async def check_referral_reward(referrer_id):
    """
    Check karega ki referrer ke 5 nayi referrals poori hui hain ya nahi.
    Agar 5 ho gayi, toh 1 Day ka Free Premium add kar dega.
    """
    user = await users_collection.find_one({"_id": referrer_id})
    if not user: 
        return False
    
    current_refs = user.get("referral_count", 0)
    rewarded_refs = user.get("rewarded_refs", 0)
    
    # Agar 5 nayi referrals aa gayi hain jo abhi tak claim/reward nahi hui
    if (current_refs - rewarded_refs) >= 5:
        now = datetime.now()
        one_day = timedelta(days=1)
        
        # Check if referrer is already a premium user
        prem_user = await premium_collection.find_one({"user_id": referrer_id})
        
        if prem_user and prem_user.get("subscription_end") > now:
            # Agar pehle se premium hai, toh uski expiry 1 din aage badha do
            new_end = prem_user["subscription_end"] + one_day
        else:
            # Agar naya ya free user hai, toh aaj se 1 din ka plan do
            new_end = now + one_day
            
        # Premium database me update karo
        await premium_collection.update_one(
            {"user_id": referrer_id},
            {"$set": {
                "user_id": referrer_id,
                "subscription_start": now, 
                "subscription_end": new_end,
                "expireAt": new_end # Agar MongoDB TTL index use karte ho
            }},
            upsert=True
        )
        
        # In 5 referrals ko 'used/rewarded' mark kar do taaki dobara na gine jayein
        await users_collection.update_one(
            {"_id": referrer_id},
            {"$inc": {"rewarded_refs": 5}}
        )
        return True # Reward mil gaya
        
    return False # Abhi 5 poore nahi hue

    # db.py ke sabse end me ye add karo
async def setup_database_indexes():
    """Bot start hote hi ye MongoDB ko kachra saaf karne ke rules bata dega"""
    try:
        # 1. Admin Logs ko exactly 30 din (2592000 seconds) baad automatically delete kar dega
        await db.admin_logs.create_index("timestamp", expireAfterSeconds=2592000)
        
        # 2. Premium Users jinka 'expireAt' time nikal chuka hai, unhe automatically premium DB se uda dega (0 seconds after expiry time)
        await premium_collection.create_index("expireAt", expireAfterSeconds=0)
        
        print("✅ MongoDB Smart Garbage Collection (TTL) Activated!")
    except Exception as e:
        print(f"⚠️ Index Setup Error: {e}")