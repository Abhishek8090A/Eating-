import os
import uuid
from threading import Thread
from flask import Flask
import telebot
from telebot import types

# ----------------- कॉन्फ़िगरेशन -----------------
TOKEN = "8202215157:AAF7wsMIhx68XoT73oxx8H1qyYTMc3SYRYg"
ADMIN_ID = 6262854630

bot = telebot.TeleBot(TOKEN)

# डेटा स्टोर करने के लिए डिक्शनरी
user_data = {}
pending_profiles = {}
approved_profiles = {}

# ----------------- Flask Keep-Alive सर्वर (Render के लिए) -----------------
app = Flask("")


@app.route("/")
def home():
  return "All India Dating Bot is Active!"


def run():
  app.run(host="0.0.0.0", port=8080)


def keep_alive():
  t = Thread(target=run)
  t.start()


# ----------------- बोट के स्टेप्स -----------------


@bot.message_handler(commands=["start"])
def send_welcome(message):
  chat_id = message.chat.id

  # अगर यूजर एडमिन है, तो एडमिन पैनल का बटन दिखाएं
  if chat_id == ADMIN_ID:
    markup_admin = types.ReplyKeyboardMarkup(
        resize_keyboard=True, one_time_keyboard=False
    )
    markup_admin.add(types.KeyboardButton("🔐 एडमिन पैनल"))
    bot.send_message(
        chat_id, "नमस्ते एडमिन जी! आपका पैनल नीचे है:", reply_markup=markup_admin
    )

  markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
  btn = types.KeyboardButton("📱 मोबाइल नंबर शेयर करें", request_contact=True)
  markup.add(btn)
  bot.send_message(
      chat_id,
      "ऑल इंडिया डेटिंग बोट में आपका स्वागत है! सुरक्षित अनुभव के लिए कृपया अपना मोबाइल नंबर साझा करें:",
      reply_markup=markup,
  )


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

  bot.send_message(
      chat_id,
      "अंतिम चरण: कृपया अपनी स्पष्ट **सेल्फ़ी (Selfie)** फोटो भेजें ताकि फर्जी प्रोफाइल रोकी जा सकें।",
      parse_mode="Markdown",
  )
  bot.register_next_step_handler(message, get_selfie)


def get_selfie(message):
  chat_id = message.chat.id
  if message.content_type == "photo":
    photo_id = message.photo[-1].file_id
    user_data[chat_id]["selfie"] = photo_id

    pending_profiles[chat_id] = user_data[chat_id]

    bot.send_message(
        chat_id,
        "🎉 आपकी सेल्फ़ी मिल गई है! एडमिन द्वारा वेरीफाई होने के बाद आपकी प्रोफाइल एक्टिव कर दी जाएगी।",
    )

    # एडमिन को अप्रूवल के लिए भेजना
    if ADMIN_ID:
      markup = types.InlineKeyboardMarkup()
      markup.add(
          types.InlineKeyboardButton(
              "✅ Approve", callback_data=f"approve_{chat_id}"
          ),
          types.InlineKeyboardButton(
              "❌ Reject", callback_data=f"reject_{chat_id}"
          ),
      )
      admin_text = (
          f"🔔 **नई प्रोफाइल वेरिफिकेशन के लिए आई है:**\nनाम: {user_data[chat_id]['name']}\nउम्र: {user_data[chat_id]['age']}\nजिला/शहर: {user_data[chat_id]['district']}"
      )
      bot.send_photo(
          ADMIN_ID, photo_id, caption=admin_text, reply_markup=markup
      )
  else:
    bot.send_message(
        chat_id, "⚠️ कृपया टेक्स्ट नहीं, बल्कि अपनी फोटो (सेल्फ़ी) ही अपलोड करें।"
    )
    bot.register_next_step_handler(message, get_selfie)


# ----------------- एडमिन पैनल और कॉलबैक हैंडलर -----------------


@bot.message_handler(
    func=lambda message: message.from_user.id == ADMIN_ID
    and message.text == "🔐 एडमिन पैनल"
)
def open_admin_panel(message):
  markup = types.InlineKeyboardMarkup()
  markup.add(
      types.InlineKeyboardButton(
          "📋 पेंडिंग प्रोफाइल्स", callback_data="admin_pending_list"
      ),
      types.InlineKeyboardButton(
          "📊 कुल यूज़र्स", callback_data="admin_stats"
      ),
  )
  bot.send_message(message.chat.id, "🔐 एडमिन डैशबोर्ड:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
  data = call.data

  if data.startswith("approve_"):
    target_id = int(data.split("_")[1])
    if target_id in pending_profiles:
      approved_profiles[target_id] = pending_profiles.pop(target_id)
      bot.send_message(
          target_id,
          "🎉 बधाई हो! आपकी प्रोफाइल अप्रूव हो गई है। अब आप बोट का उपयोग कर सकते हैं।",
      )
      bot.edit_message_caption(
          chat_id=call.message.chat.id,
          message_id=call.message.message_id,
          caption=call.message.caption + "\n\n✅ **Status: Approved**",
      )

  elif data.startswith("reject_"):
    target_id = int(data.split("_")[1])
    if target_id in pending_profiles:
      pending_profiles.pop(target_id)
      bot.send_message(
          target_id,
          "❌ खेद है, आपकी सेल्फ़ी या जानकारी रिजेक्ट कर दी गई है। कृपया /start से दोबारा प्रयास करें।",
      )
      bot.edit_message_caption(
          chat_id=call.message.chat.id,
          message_id=call.message.message_id,
          caption=call.message.caption + "\n\n❌ **Status: Rejected**",
      )

  elif data == "admin_stats":
    total_approved = len(approved_profiles)
    total_pending = len(pending_profiles)
    bot.answer_callback_query(
        call.id,
        f"Approved: {total_approved} | Pending: {total_pending}",
        show_alert=True,
    )


# ----------------- फ्री वीडियो कॉल लिंक जनरेटर फंक्शन -----------------


def send_video_call_link(chat_id_1, chat_id_2):
  room_id = str(uuid.uuid4())[:8]
  call_link = f"https://meet.jit.si/AllIndiaDating_{room_id}"

  markup = types.InlineKeyboardMarkup()
  btn_call = types.InlineKeyboardButton("🎥 वीडियो कॉल से जुड़ें", url=call_link)
  markup.add(btn_call)

  message_text = (
      "🎉 **बधाई हो! आपका मैच बन गया है!**\n\nसुरक्षित और प्राइवेट वीडियो कॉल के लिए नीचे दिए गए बटन पर क्लिक करें। यह लिंक केवल आप दोनों के लिए है और कॉल कटने के बाद स्वतः बंद हो जाता है।"
  )

  bot.send_message(chat_id_1, message_text, reply_markup=markup)
  bot.send_message(chat_id_2, message_text, reply_markup=markup)


# ----------------- बोट और सर्वर रन करना -----------------
if __name__ == "__main__":
  keep_alive()
  print("बोट और वीडियो कॉल एपीआई सफलतापूर्वक शुरू हो गई है...")
  bot.infinity_polling()

