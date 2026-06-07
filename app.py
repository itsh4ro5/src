import os
import sys
import subprocess
import psutil
from quart import Quart, jsonify, render_template, request
from utils.db import premium_collection, db, users_collection
import datetime

# 🟢 Hugging Face Secrets se Owner ID fetch karna
# Agar secret nahi milta toh fallback ke liye purani ID rakhi hai
OWNER_ID = int(os.getenv("OWNER_ID", 0000000000))

# 🟢 SAFEST BOT STARTER
def start_bot_safely():
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            if proc.info['cmdline'] and 'main.py' in proc.info['cmdline']:
                print("✅ Bot is already running in background.")
                return
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        pass
        
    print("🚀 Starting Main Bot Process...")
    try:
        subprocess.Popen([sys.executable, "main.py"], 
                         stdout=sys.stdout, 
                         stderr=sys.stderr,
                         start_new_session=True)
    except Exception as e:
        print(f"⚠️ Failed to start bot: {e}")

# App start hote hi bot on hoga
start_bot_safely()

app = Quart(__name__)

@app.route("/")
async def index():
    return "H4R SRC BOT IS RUNNING... (Phase 4 Active)"

@app.route("/dashboard")
async def dashboard_page():
    return await render_template("dashboard.html")

@app.route("/api/status/<int:uid>")
async def get_dashboard_data(uid):
    try:
        # 🟢 ROLE & PREMIUM LOGIC
        is_owner = (uid == OWNER_ID)
        prem = await premium_collection.find_one({"user_id": uid})
        
        if is_owner:
            role = "owner"
            is_premium = True
            expiry = "INFINITY ♾️" # Owner ka kabhi expire nahi hoga
        elif prem:
            role = "premium"
            is_premium = True
            expiry = prem["subscription_end"].strftime("%d %b, %y")
        else:
            role = "free"
            is_premium = False
            expiry = "N/A"

        # Live Progress fetch karna
        live = await db["live_status"].find_one({"user_id": uid}, {"_id": 0})
        
        # History fetch karna
        hist_cursor = db["history"].find({"user_id": uid}).sort("timestamp", -1).limit(10)
        hist = []
        async for h in hist_cursor:
            hist.append({
                "source": h.get("source", "Unknown"),
                "dest": h.get("destination", "Unknown"),
                "count": h.get("count", 0),
                "date": h.get("timestamp").strftime("%d %b") if "timestamp" in h else "N/A"
            })

        # Admin Data (Sirf Owner ke liye)
        admin_users = None
        if is_owner:
            users_cursor = users_collection.find().limit(50)
            admin_users = []
            async for u in users_cursor:
                # Telegram usually 'first_name' save karta hai
                name = u.get("first_name", u.get("username", "Unknown User"))
                admin_users.append({
                    "id": str(u["_id"]),
                    "name": name
                })

        return jsonify({
            "role": role,
            "is_premium": is_premium,
            "expiry": expiry,
            "live": live,
            "history": hist,
            "admin_users": admin_users
        })
    except Exception as e:
        print(f"API Error: {e}")
        return jsonify({"error": str(e)}), 500

# Admin Actions (Block/Warn)
@app.route("/api/admin/action", methods=["POST"])
async def admin_action():
    data = await request.get_json()
    admin_id = data.get("admin_id")
    
    if admin_id != OWNER_ID:
        return jsonify({"error": "Unauthorized"}), 403
    
    target_id = data.get("target_id")
    action = data.get("action")
    
    if action == "block":
        await users_collection.update_one({"_id": target_id}, {"$set": {"is_blocked": True}})
    elif action == "warn":
        # Yahan aap apna warning logic add kar sakte hain
        pass
        
    return jsonify({"status": "success"})

@app.route("/profile")
async def profile_page():
    return await render_template("profile.html")

@app.route("/api/profile/<int:uid>")
async def get_profile_data(uid):
    try:
        user = await users_collection.find_one({"_id": uid})
        prem = await premium_collection.find_one({"user_id": uid})
        
        is_owner = (uid == int(os.getenv("OWNER_ID", 5842838338)))
        role = "owner" if is_owner else ("premium" if prem else "free")
        expiry = "INFINITY ♾️" if is_owner else (prem["subscription_end"].strftime("%d %b, %y") if prem else "N/A")
        
        # Stats Calculation
        total_tasks = await db["history"].count_documents({"user_id": uid})
        pipeline = [{"$match": {"user_id": uid}}, {"$group": {"_id": None, "total": {"$sum": "$count"}}}]
        agg = await db["history"].aggregate(pipeline).to_list(length=1)
        total_cloned = agg[0]["total"] if agg else 0

        join_date = user.get("join_date", datetime.datetime.now()).strftime("%b %Y") if user and "join_date" in user else "Unknown"
        name = user.get("first_name", user.get("username", "Guest")) if user else "Guest"

        return jsonify({
            "name": name,
            "role": role,
            "expiry": expiry,
            "join_date": join_date,
            "total_tasks": total_tasks,
            "total_cloned": total_cloned
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/commands")
async def commands_page():
    return await render_template("commands.html")

@app.route("/activity")
async def activity_page():
    return await render_template("activity.html")

@app.route("/api/file_logs/<int:uid>")
async def get_file_logs(uid):
    try:
        # DB se sirf latest 20 file logs uthayenge real-time me
        logs_cursor = db["file_logs"].find({"user_id": uid}).sort("timestamp", -1).limit(20)
        logs = []
        async for l in logs_cursor:
            logs.append({
                "status": l.get("status", "success"),
                "file_name": l.get("file_name", "Unknown File"),
                "source": l.get("source", "Source"),
                "dest": l.get("dest", "Destination"),
                "orig_caption": l.get("orig_caption", "No caption"),
                "ai_caption": l.get("ai_caption", "No AI caption"),
                "time_taken": l.get("time_taken", "0.0s"),
                "break_time": l.get("break_time", "0.0s"),
                "time": l.get("timestamp").strftime("%H:%M:%S") if "timestamp" in l else "N/A"
            })
        return jsonify({"logs": logs})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    app.run(host="0.0.0.0", port=port)