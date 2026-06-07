# theme_config.py
import os

# 📂 FONT FOLDER PATH
# Is folder me aapko apni saari .ttf files upload karni hain
FONT_DIR = "fonts"

# Agar folder nahi hai, toh auto-create kar dega
if not os.path.exists(FONT_DIR):
    os.makedirs(FONT_DIR)

# 🔠 20+ FONT STYLES (In files ko fonts/ folder me upload karna hoga)
AVAILABLE_FONTS = {
    "default.ttf": "Standard Font",
    "impact.ttf": "𝗕𝗢𝗟𝗗 𝗜𝗠𝗣𝗔𝗖𝗧",
    "hacker.ttf": "🄷🄰🄲🄺🄴🅁 🄶🄻🄸🅃🄲🄷",
    "comic.ttf": "𝘊𝘰𝘮𝘪𝘤 𝘚𝘵𝘺𝘭𝘦",
    "neon.ttf": "Nҽ𝘰n Lιg𝘩t",
    "cyber.ttf": "C Y B E R",
    "pixel.ttf": "P1X3L 8-B1T",
    "roboto.ttf": "Roboto Clean",
    "arial_bold.ttf": "Arial Bold",
    "gothic.ttf": "𝕲𝘰𝘵𝘩𝘪𝘤 𝕯𝘢𝘳𝘬",
    "matrix.ttf": "MΛTRIX",
    "vintage.ttf": "𝓥𝘪𝘯𝘵𝘢𝘨𝘦 𝓡𝘦𝘵𝘳𝘰",
    "future.ttf": "F U T U R E",
    "monster.ttf": "M O N S T E R",
    "cursive.ttf": "𝓒𝓾𝓻𝓼𝓲𝓿𝓮 𝓛𝓸𝓿𝓮",
    "elegant.ttf": "𝔼𝘭𝘦𝘨𝘢𝘯𝘵 𝕾𝘦𝘳𝘪𝘧",
    "space.ttf": "S P A C E",
    "bold_italic.ttf": "𝘽𝗼𝙡𝗱 𝙄𝙩𝙖𝙡𝙞𝙘",
    "typewriter.ttf": "Tʏp𝘦wʀiᴛeʀ",
    "graffiti.ttf": "G𝕣a𝘧fιt𝘪",
    "ninja.ttf": "🥷 N I N J A"
}

# 🎨 100+ PREMIUM COLORS FOR TEXT WATERMARK
AVAILABLE_COLORS = {
    # ⚪ Standard Colors
    "white": "⚪ White", "black": "⚫ Black", "red": "🔴 Red", "blue": "🔵 Blue", 
    "green": "🟢 Green", "yellow": "🟡 Yellow", "orange": "🟠 Orange", "purple": "🟣 Purple",
    "brown": "🟤 Brown", "pink": "🌸 Pink", "gray": "🔘 Gray", "silver": "🪙 Silver",

    # 🟢 Neon & Cyberpunk Colors
    "#39FF14": "🟢 Neon Green", "#00FFFF": "🔵 Cyan / Aqua", "#FF00FF": "🟣 Magenta", 
    "#FF1493": "💖 Deep Pink", "#00FF00": "🟩 Lime", "#FFFF00": "🟨 Cyber Yellow",
    "#FF4500": "🔥 Orange Red", "#8A2BE2": "🎀 Deep Pink", "#7FFF00": "🎾 Chartreuse",

    # 🟡 Gold & Premium Colors
    "#FFD700": "🟡 Gold", "#DAA520": "🍯 Goldenrod", "#B8860B": "🪙 Dark Goldenrod",
    "#CD7F32": "🏆 Peru / Bronze", "#C0C0C0": "⚙️ Silver Pro", "#E5E4E2": "💿 Platinum",

    # 🔵 Blue Variants
    "#1E90FF": "🌊 Dodger Blue", "#00BFFF": "💦 Deep Sky Blue", "#4682B4": "👖 Steel Blue",
    "#4169E1": "🧿 Royal Blue", "#000080": "🌌 Navy", "#191970": "🌃 Midnight Blue",
    "#00CED1": "💧 Dark Turquoise", "#5F9EA0": "🎽 Cadet Blue", "#ADD8E6": "🧊 Light Blue",

    # 🔴 Red & Pink Variants
    "#DC143C": "🩸 Crimson", "#B22222": "🧱 Firebrick", "#8B0000": "🍷 Dark Red",
    "#FF69B4": "👙 Hot Pink", "#FFB6C1": "🩰 Light Pink", "#C71585": "🌺 Medium Violet Red",
    "#FA8072": "🍣 Salmon", "#E9967A": "🦐 Dark Salmon", "#F08080": "🥩 Light Coral",

    # 🟢 Green Variants
    "#228B22": "🌲 Forest Green", "#006400": "🌳 Dark Green", "#2E8B57": "🌿 Sea Green",
    "#3CB371": "🍀 Medium Sea Green", "#8FBC8F": "🔋 Dark Sea Green", "#98FB98": "🍵 Pale Green",
    "#00FA9A": "🍈 Medium Spring Green", "#9ACD32": "🥝 Yellow Green", "#6B8E23": "🫒 Olive Drab",

    # 🟣 Purple & Violet Variants
    "#800080": "🍇 Purple", "#9370DB": "🍆 Medium Purple", "#8B008B": "🔮 Dark Magenta",
    "#9400D3": "🍠 Dark Violet", "#9932CC": "🌂 Dark Orchid", "#BA55D3": "👚 Medium Orchid",
    "#DDA0DD": "🪻 Plum", "#EE82EE": "🪁 Violet", "#DA70D6": "🪀 Orchid",

    # 🟠 Orange & Brown Variants
    "#FF8C00": "🎃 Dark Orange", "#D2691E": "🐫 Goldenrod", "#8B4513": "👞 Saddle Brown",
    "#A0522D": "🧳 Sienna", "#D2B48C": "🐪 Tan", "#DEB887": "🪵 Burlywood",
    "#F4A460": "🪑 Sandy Brown", "#BC8F8F": "🏕️ Rosy Brown", "#F0E68C": "🌾 Khaki",

    # ⚪ Pastel & Light Colors
    "#FFDAB9": "🍑 Peach Puff", "#FFE4B5": "🥟 Moccasin", "#FFEFD5": "🧈 Papaya Whip",
    "#FFFACD": "🍋 Lemon Chiffon", "#FAFAD2": "🍌 Light Goldenrod", "#E0FFFF": "🧼 Light Cyan",
    "#F0FFF0": "🍯 Honeydew", "#F5FFFA": "🥛 Mint Cream", "#F0F8FF": "🥣 Alice Blue",
    "#FFF0F5": "🧂 Lavender Blush", "#FFE4E1": "🌸 Misty Rose", "#FFF5EE": "🐚 Seashell",

    # ⚫ Dark & Sleek Colors
    "#2F4F4F": "🪨 Dark Slate Gray", "#708090": "🗻 Slate Gray", "#A9A9A9": "🐭 Dark Gray",
    "#696969": "🐘 Dim Gray", "#778899": "🦈 Light Slate Gray", "#2C3E50": "🌚 Dark Blue Gray"
}
