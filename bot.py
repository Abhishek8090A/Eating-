import os
import uuid
from datetime import date
from threading import Thread
from flask import Flask
import telebot
from telebot import types

# ----------------- कॉन्फ़िगरेशन -----------------
TOKEN = "8202215157:AAF7wsMIhx68XoT73oxx8H1qyYTMc3SYRYg"
ADMIN_ID = 6262854630

bot = telebot.TeleBot(TOKEN)

# ----------------- डेटाबेस (डिक्शनरी) -----------------
user_data = {}
pending_profiles = {}
approved_profiles = {}

# डायनामिक सेटिंग्स (QR, सपोर्ट, और पॉइंट्स कंट्रोल)
bot_settings = {
    "upi_qr_file_id": None,
    "support_contact": "@YourAdminUsername",
    "daily_bonus_coins": 10,
    "refer_coins": 50
}

# कॉइन्स और डेली बोनस ट्रैक करने के लिए
user_coins = {}
last_bonus_date = {}

# ----------------- Flask Keep-Alive सर्वर (Render के लिए) -----------------
app = Flask("")

@app.route("/")
def home():
    return "All India Dating Bot is Active!"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# ----------------- बोट स्टार्ट और मेनू -----------------

@bot.message_handler(commands=["start"])
def send_welcome(message):
    chat_id = message.chat.id

    # 1. अगर यूजर एडमिन है
    if chat_id == ADMIN_ID:
        markup_admin = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
        markup_admin.add(types.KeyboardButton("🔐 एडमिन पैनल"))
        bot.send_message(chat_id, "नमस्ते एडमिन जी! आपका पैनल नीचे है:", reply_markup=markup_admin)
        return

    # 2. रेफरल सिस्टम चेक (अगर किसी ने रेफरल लिंक से शुरू किया है)
    text = message.text
    if len(text.split()) > 1:
        ref_id = text.split()[1]
        if ref_id.isdigit():
            referrer_id = int(ref_id)
            if referrer_id in approved_profiles and referrer_id != chat_id:
                reward = bot_settings["refer_coins"]
                user_coins[referrer_id] = user_coins.get(referrer_id, 0) + reward
                bot.send_message(referrer_id, f"🎉 बधाई हो! आपके लिंक से एक नए यूजर ने ज्वाइन किया है। आपको **+{reward} Coins** मिले हैं!", parse_mode="Markdown")

    # 3. अगर यूजर पहले से अप्रूव्ड है - शानदार 2-कॉलम ग्रिड मेनू दिखाएं
    if chat_id in approved_profiles:
        markup_menu = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        
        btn_find = types.KeyboardButton("🔍 पार्टनर खोजें")
        btn_matches = types.KeyboardButton("💌 मेरे मैच")
        btn_profile = types.KeyboardButton("👤 मेरी प्रोफाइल")
        btn_bonus = types.KeyboardButton("🎁 डेली बोनस")
        btn_vip = types.KeyboardButton("💎 VIP फीचर्स")
        btn_invite = types.KeyboardButton("👥 रेफर एंड अर्न")
        btn_support = types.KeyboardButton("🎧 हेल्प / सपोर्ट")
        
        markup_menu.add(btn_find, btn_matches, btn_profile, btn_bonus, btn_vip, btn_invite)
        markup_menu.row(btn_support)
        
        bot.send_message(chat_id, "✨ आपका स्वागत है! कृपया नीचे दिए गए मेनू से विकल्प चुनें:", reply_markup=markup_menu)
        return

    # 4. अगर यूजर पेंडिंग लिस्ट में है
    if chat_id in pending_profiles:
        bot.send_message(chat_id, "⏳ आपकी प्रोफाइल अभी एडमिन के पास वेरिफिकेशन के लिए पेंडिंग है। कृपया प्रतीक्षा करें।")
        return

    # 5. नए यूजर के लिए रजिस्ट्रेशन शुरू करें
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    btn = types.KeyboardButton("📱 मोबाइल नंबर शेयर करें", request_contact=True)
    markup.add(btn)
    bot.send_message(
        chat_id,
        "ऑल इंडिया डेटिंग बोट में आपका स्वागत है! सुरक्षित अनुभव के लिए कृपया अपना मोबाइल नंबर साझा करें:",
        reply_markup=markup,
    )

# ----------------- रजिस्ट्रेशन सिस्टम -----------------

@bot.message_handler(content_types=["contact"])
def handle_contact(message):
    chat_id = message.chat.id
    phone_number = message.contact.phone_number
    user_data[chat_id] = {"phone": phone_number}
    bot.send_message(chat_id, "✅ नंबर वेरिफाई हो गया!\n\nअब अपना पूरा नाम दर्ज करें:")
    bot.register_next_step_handler(message, get_name)

def get_name(message):
    chat_id = message.chat.id
    user_data[chat_id]["name"] = message.text
    bot.send_message(chat_id, "आपकी उम्र (Age) क्या है?")
    bot.register_next_step_handler(message, get_age)

def get_age(message):
    chat_id = message.chat.id
    user_data[chat_id]["age"] = message.text
    bot.send_message(chat_id, "जिला / शहर:")
    bot.register_next_step_handler(message, get_district)

def get_district(message):
    chat_id = message.chat.id
    user_data[chat_id]["district"] = message.text
    bot.send_message(chat_id, "अंतिम चरण: कृपया अपनी स्पष्ट **सेल्फ़ी (Selfie)** फोटो भेजें।", parse_mode="Markdown")
    bot.register_next_step_handler(message, get_selfie)

def get_selfie(message):
    chat_id = message.chat.id
    if message.content_type == "photo":
        photo_id = message.photo[-1].file_id
        user_data[chat_id]["selfie"] = photo_id
        pending_profiles[chat_id] = user_data[chat_id]
        
        if chat_id not in user_coins:
            user_coins[chat_id] = 0

        bot.send_message(chat_id, "🎉 आपकी सेल्फ़ी मिल गई है! एडमिन द्वारा वेरीफाई होने के बाद प्रोफाइल एक्टिव हो जाएगी।")

        if ADMIN_ID:
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("✅ Approve", callback_data=f"approve_{chat_id}"),
                types.InlineKeyboardButton("❌ Reject", callback_data=f"reject_{chat_id}")
            )
            admin_text = f"🔔 **नई प्रोफाइल:**\nनाम: {user_data[chat_id]['name']}\nउम्र: {user_data[chat_id]['age']}\nशहर: {user_data[chat_id]['district']}"
            bot.send_photo(ADMIN_ID, photo_id, caption=admin_text, reply_markup=markup)
    else:
        bot.send_message(chat_id, "⚠️ कृपया अपनी फोटो (सेल्फ़ी) ही अपलोड करें।")
        bot.register_next_step_handler(message, get_selfie)

# ----------------- एडमिन पैनल और सेटिंग्स कंट्रोल -----------------

@bot.message_handler(func=lambda message: message.from_user.id == ADMIN_ID and message.text == "🔐 एडमिन पैनल")
def open_admin_panel(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    btn_pending = types.InlineKeyboardButton("📋 पेंडिंग प्रोफाइल्स", callback_data="admin_pending_list")
    btn_stats = types.InlineKeyboardButton("📊 कुल यूज़र्स", callback_data="admin_stats")
    btn_set_qr = types.InlineKeyboardButton("📲 UPI QR बदलें", callback_data="admin_set_qr")
    btn_set_support = types.InlineKeyboardButton("🎧 सपोर्ट ID बदलें", callback_data="admin_set_support")
    btn_set_bonus = types.InlineKeyboardButton("🎁 बोनस कॉइन्स सेट करें", callback_data="admin_set_bonus")
    btn_set_refer = types.InlineKeyboardButton("👥 रेफर कॉइन्स सेट करें", callback_data="admin_set_refer")
    
    markup.add(btn_pending, btn_stats, btn_set_qr, btn_set_support, btn_set_bonus, btn_set_refer)
    
    bot.send_message(
        message.chat.id, 
        f"🔐 **एडमिन डैशबोर्ड:**\n\n"
        f"• वर्तमान डेली बोनस: `{bot_settings['daily_bonus_coins']}` Coins\n"
        f"• वर्तमान रेफर कॉइन्स: `{bot_settings['refer_coins']}` Coins\n\n"
        f"नीचे दिए गए विकल्पों में से चुनें:", 
        reply_markup=markup, 
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    data = call.data
    chat_id = call.message.chat.id

    if data.startswith("approve_"):
        target_id = int(data.split("_")[1])
        if target_id in pending_profiles:
            approved_profiles[target_id] = pending_profiles.pop(target_id)
            bot.send_message(target_id, "🎉 आपकी प्रोफाइल अप्रूव हो गई है। मुख्य मेनू देखने के लिए /start भेजें।")
            bot.edit_message_caption(chat_id=chat_id, message_id=call.message.message_id, caption=call.message.caption + "\n\n✅ **Approved**")

    elif data.startswith("reject_"):
        target_id = int(data.split("_")[1])
        if target_id in pending_profiles:
            pending_profiles.pop(target_id)
            bot.send_message(target_id, "❌ आपकी जानकारी रिजेक्ट कर दी गई है। कृपया /start से दोबारा प्रयास करें।")
            bot.edit_message_caption(chat_id=chat_id, message_id=call.message.message_id, caption=call.message.caption + "\n\n❌ **Rejected**")

    elif data == "admin_pending_list":
        if not pending_profiles:
            bot.answer_callback_query(call.id, "कोई भी पेंडिंग प्रोफाइल नहीं है।", show_alert=True)
        else:
            bot.answer_callback_query(call.id, f"कुल पेंडिंग प्रोफाइल्स: {len(pending_profiles)}", show_alert=True)

    elif data == "admin_stats":
        bot.answer_callback_query(call.id, f"Approved: {len(approved_profiles)} | Pending: {len(pending_profiles)}", show_alert=True)

    elif data == "admin_set_qr":
        msg = bot.send_message(chat_id, "कृपया नया **UPI QR Code (Photo)** भेजें:")
        bot.register_next_step_handler(msg, save_upi_qr)
        
    elif data == "admin_set_support":
        msg = bot.send_message(chat_id, "कृपया हेल्प/सपोर्ट के लिए अपना नया टेलीग्राम Username (जैसे @AdminHelp) लिखकर भेजें:")
        bot.register_next_step_handler(msg, save_support_contact)

    elif data == "admin_set_bonus":
        msg = bot.send_message(chat_id, "डेली बोनस में कितने कॉइन्स देना चाहते हैं? (केवल अंक जैसे: 15 या 20 लिखें):")
        bot.register_next_step_handler(msg, save_bonus_amount)

    elif data == "admin_set_refer":
        msg = bot.send_message(chat_id, "रेफर करने पर कितने कॉइन्स देना चाहते हैं? (केवल अंक जैसे: 50 या 100 लिखें):")
        bot.register_next_step_handler(msg, save_refer_amount)

def save_upi_qr(message):
    if message.content_type == 'photo':
        bot_settings["upi_qr_file_id"] = message.photo[-1].file_id
        bot.send_message(message.chat.id, "✅ UPI QR Code सफलतापूर्वक अपडेट हो गया है!")
    else:
        bot.send_message(message.chat.id, "⚠️ कृपया सिर्फ फोटो भेजें।")

def save_support_contact(message):
    if message.text:
        bot_settings["support_contact"] = message.text
        bot.send_message(message.chat.id, f"✅ सपोर्ट कांटेक्ट अपडेट हुआ: {message.text}")
    else:
        bot.send_message(message.chat.id, "⚠️ कृपया टेक्स्ट भेजें।")

def save_bonus_amount(message):
    if message.text.isdigit():
        bot_settings["daily_bonus_coins"] = int(message.text)
        bot.send_message(message.chat.id, f"✅ डेली बोनस अब अपडेट होकर `{message.text} Coins` हो गया है!", parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, "⚠️ कृपया केवल सही अंक (Number) भेजें।")

def save_refer_amount(message):
    if message.text.isdigit():
        bot_settings["refer_coins"] = int(message.text)
        bot.send_message(message.chat.id, f"✅ रेफर रिवॉर्ड अब अपडेट होकर `{message.text} Coins` हो गया है!", parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, "⚠️ कृपया केवल सही अंक (Number) भेजें।")


# ----------------- यूज़र मेनू बटन्स हैंडलर्स -----------------

@bot.message_handler(func=lambda message: message.text == "🔍 पार्टनर खोजें")
def find_partner(message):
    bot.send_message(message.chat.id, "🔍 आपके लिए पूरे भारत में सबसे बेहतरीन मैच ढूंढे जा रहे हैं... कृपया प्रतीक्षा करें।")

@bot.message_handler(func=lambda message: message.text == "💌 मेरे मैच")
def my_matches(message):
    bot.send_message(message.chat.id, "💌 यहाँ आपके वे मैच दिखेंगे जिन्होंने आपको लाइक किया है। (जल्द आ रहा है!)")

@bot.message_handler(func=lambda message: message.text == "👤 मेरी प्रोफाइल")
def my_profile(message):
    chat_id = message.chat.id
    if chat_id in approved_profiles:
        p = approved_profiles[chat_id]
        coins = user_coins.get(chat_id, 0)
        profile_text = (
            f"👤 **आपकी प्रोफाइल विवरण:**\n\n"
            f"नाम: {p['name']}\nउम्र: {p['age']}\nजिला/शहर: {p['district']}\n\n"
            f"💰 **आपके कॉइन्स:** {coins} Coins"
        )
        bot.send_photo(chat_id, p["selfie"], caption=profile_text, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "🎁 डेली बोनस")
def daily_bonus(message):
    chat_id = message.chat.id
    if chat_id in approved_profiles:
        today = str(date.today())
        if last_bonus_date.get(chat_id) == today:
            bot.send_message(chat_id, "⚠️ आप आज का बोनस पहले ही ले चुके हैं। कृपया कल दोबारा आएं!")
        else:
            reward = bot_settings["daily_bonus_coins"]
            user_coins[chat_id] = user_coins.get(chat_id, 0) + reward
            last_bonus_date[chat_id] = today
            
            bot.send_message(
                chat_id, 
                f"🎉 **बधाई हो!** आपको आज का डेली बोनस मिल गया है।\n\n"
                f"💰 **मिले:** +{reward} Coins\n"
                f"💼 **कुल बैलेंस:** {user_coins[chat_id]} Coins",
                parse_mode="Markdown"
            )
    else:
        bot.send_message(chat_id, "⚠️ पहले अपनी प्रोफाइल अप्रूव करवाएं।")

@bot.message_handler(func=lambda message: message.text == "💎 VIP फीचर्स")
def vip_features(message):
    chat_id = message.chat.id
    vip_text = "💎 **VIP मेम्बरशिप**\n\n☑️ प्रोफाइल पर ब्लू टिक\n♾️ अनलिमिटेड चैट्स और मैच\n\n**VIP बनने के लिए नीचे दिए गए QR Code पर पेमेंट करें और सपोर्ट को स्क्रीनशॉट भेजें:**"
    
    if bot_settings.get("upi_qr_file_id"):
        bot.send_photo(chat_id, bot_settings["upi_qr_file_id"], caption=vip_text, parse_mode="Markdown")
    else:
        bot.send_message(chat_id, vip_text + "\n\n*(QR Code अभी उपलब्ध नहीं है, कृपया सपोर्ट से बात करें।)*", parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "👥 रेफर एंड अर्न")
def invite_friends(message):
    chat_id = message.chat.id
    if chat_id in approved_profiles:
        bot_info = bot.get_me()
        refer_link = f"https://t.me/{bot_info.username}?start={chat_id}"
        reward = bot_settings["refer_coins"]
        
        invite_text = (
            f"👥 **रेफर एंड अर्न (Invite & Earn)**\n\n"
            f"अपने दोस्तों को यह बोट शेयर करें! जब आपका दोस्त इस लिंक से ज्वाइन करेगा, तो आपको तुरंत **{reward} Coins** मिलेंगे।\n\n"
            f"🔗 **आपका पर्सनल रेफरल लिंक:**\n`{refer_link}`\n\n"
            f"*(लिंक पर क्लिक करके कॉपी करें)*"
        )
        bot.send_message(chat_id, invite_text, parse_mode="Markdown")
    else:
        bot.send_message(chat_id, "⚠️ पहले अपनी प्रोफाइल अप्रूव करवाएं।")

@bot.message_handler(func=lambda message: message.text == "🎧 हेल्प / सपोर्ट")
def help_support(message):
    support_id = bot_settings.get("support_contact", "@YourAdminUsername")
    bot.send_message(message.chat.id, f"🎧 किसी भी समस्या, रिपोर्ट या पेमेंट स्क्रीनशॉट के लिए सपोर्ट से संपर्क करें:\n\n👉 **{support_id}**", parse_mode="Markdown")

# ----------------- बोट और सर्वर रन करना -----------------
if __name__ == "__main__":
    keep_alive()
    print("ऑल इंडिया डेटिंग बोट सफलतापूर्वक शुरू हो गया है...")
    bot.infinity_polling()
