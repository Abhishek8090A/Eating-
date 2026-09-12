import os
import uuid
from datetime import date
from threading import Thread
from flask import Flask
import telebot
from telebot import types

# ----------------- Configuration -----------------
TOKEN = "8202215157:AAF7wsMIhx68XoT73oxx8H1qyYTMc3SYRYg"
ADMIN_ID = 6262854630

bot = telebot.TeleBot(TOKEN)

# ----------------- Database (Dictionaries & Sets) -----------------
user_data = {}
pending_profiles = {}
approved_profiles = {}
blocked_users = set()  # Stores blocked user IDs

# Dynamic settings (QR, support, points control, and VIP price)
bot_settings = {
    "upi_qr_file_id": None,
    "support_contact": "@YourAdminUsername",
    "daily_bonus_coins": 10,
    "refer_coins": 50,
    "vip_price": "₹199"  # Default VIP Price
}

# Tracking coins and daily bonuses
user_coins = {}
last_bonus_date = {}

# ----------------- Flask Keep-Alive Server (For Render) -----------------
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

# ----------------- Bot Start & Menu -----------------

@bot.message_handler(commands=["start"])
def send_welcome(message):
    chat_id = message.chat.id

    # Check if user is blocked
    if chat_id in blocked_users:
        bot.send_message(chat_id, "🚫 Your account has been blocked by the admin.")
        return

    # 1. If user is admin
    if chat_id == ADMIN_ID:
        markup_admin = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
        markup_admin.add(types.KeyboardButton("🔐 Admin Panel"))
        bot.send_message(chat_id, "Hello Admin! Your panel is below:", reply_markup=markup_admin)
        return

    # 2. Referral system check (if started via referral link)
    text = message.text
    if len(text.split()) > 1:
        ref_id = text.split()[1]
        if ref_id.isdigit():
            referrer_id = int(ref_id)
            if referrer_id in approved_profiles and referrer_id != chat_id:
                reward = bot_settings["refer_coins"]
                user_coins[referrer_id] = user_coins.get(referrer_id, 0) + reward
                bot.send_message(referrer_id, f"🎉 Congratulations! A new user has joined using your link. You received **+{reward} Coins**!", parse_mode="Markdown")

    # 3. If user is already approved - show 2-column grid menu
    if chat_id in approved_profiles:
        markup_menu = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        
        btn_find = types.KeyboardButton("🔍 Find Partner")
        btn_matches = types.KeyboardButton("💌 My Matches")
        btn_profile = types.KeyboardButton("👤 My Profile")
        btn_bonus = types.KeyboardButton("🎁 Daily Bonus")
        btn_vip = types.KeyboardButton("💎 VIP Features")
        btn_invite = types.KeyboardButton("👥 Refer & Earn")
        btn_report = types.KeyboardButton("🚨 Report Issue")
        btn_support = types.KeyboardButton("🎧 Help / Support")
        
        markup_menu.add(btn_find, btn_matches, btn_profile, btn_bonus, btn_vip, btn_invite, btn_report)
        markup_menu.row(btn_support)
        
        bot.send_message(chat_id, "✨ Welcome! Please select an option from the menu below:", reply_markup=markup_menu)
        return

    # 4. If user is in the pending list
    if chat_id in pending_profiles:
        bot.send_message(chat_id, "⏳ Your profile is currently pending verification with the admin. Please wait.")
        return

    # 5. Start registration for new users
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    btn = types.KeyboardButton("📱 Share Mobile Number", request_contact=True)
    markup.add(btn)
    bot.send_message(
        chat_id,
        "Welcome to the All India Dating Bot! For a secure experience, please share your mobile number:",
        reply_markup=markup,
    )

# ----------------- Registration System -----------------

@bot.message_handler(content_types=["contact"])
def handle_contact(message):
    chat_id = message.chat.id
    if chat_id in blocked_users:
        return
    phone_number = message.contact.phone_number
    user_data[chat_id] = {"phone": phone_number}
    bot.send_message(chat_id, "✅ Number verified!\n\nNow enter your full name:")
    bot.register_next_step_handler(message, get_name)

def get_name(message):
    chat_id = message.chat.id
    user_data[chat_id]["name"] = message.text
    bot.send_message(chat_id, "What is your age?")
    bot.register_next_step_handler(message, get_age)

def get_age(message):
    chat_id = message.chat.id
    user_data[chat_id]["age"] = message.text
    bot.send_message(chat_id, "District / City:")
    bot.register_next_step_handler(message, get_district)

def get_district(message):
    chat_id = message.chat.id
    user_data[chat_id]["district"] = message.text
    bot.send_message(chat_id, "Final Step: Please send a clear **Selfie** photo.", parse_mode="Markdown")
    bot.register_next_step_handler(message, get_selfie)

def get_selfie(message):
    chat_id = message.chat.id
    if message.content_type == "photo":
        photo_id = message.photo[-1].file_id
        user_data[chat_id]["selfie"] = photo_id
        pending_profiles[chat_id] = user_data[chat_id]
        
        if chat_id not in user_coins:
            user_coins[chat_id] = 0

        bot.send_message(chat_id, "🎉 Your selfie has been received! Your profile will be activated after admin verification.")

        if ADMIN_ID:
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("✅ Approve", callback_data=f"approve_{chat_id}"),
                types.InlineKeyboardButton("❌ Reject", callback_data=f"reject_{chat_id}")
            )
            admin_text = f"🔔 **New Profile:**\nUser ID: `{chat_id}`\nName: {user_data[chat_id]['name']}\nAge: {user_data[chat_id]['age']}\nCity: {user_data[chat_id]['district']}"
            bot.send_photo(ADMIN_ID, photo_id, caption=admin_text, reply_markup=markup, parse_mode="Markdown")
    else:
        bot.send_message(chat_id, "⚠️ Please upload a photo (selfie) only.")
        bot.register_next_step_handler(message, get_selfie)

# ----------------- Admin Panel & Settings Control -----------------

@bot.message_handler(func=lambda message: message.from_user.id == ADMIN_ID and message.text == "🔐 Admin Panel")
def open_admin_panel(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    btn_pending = types.InlineKeyboardButton("📋 Pending Profiles", callback_data="admin_pending_list")
    btn_stats = types.InlineKeyboardButton("📊 Total Users", callback_data="admin_stats")
    btn_block_user = types.InlineKeyboardButton("🚫 Block User", callback_data="admin_block_prompt")
    btn_unblock_user = types.InlineKeyboardButton("✅ Unblock User", callback_data="admin_unblock_prompt")
    btn_delete_user = types.InlineKeyboardButton("🗑️ Delete User", callback_data="admin_delete_prompt")
    btn_set_qr = types.InlineKeyboardButton("📲 Change UPI QR", callback_data="admin_set_qr")
    btn_set_support = types.InlineKeyboardButton("🎧 Change Support ID", callback_data="admin_set_support")
    btn_set_bonus = types.InlineKeyboardButton("🎁 Set Bonus Coins", callback_data="admin_set_bonus")
    btn_set_refer = types.InlineKeyboardButton("👥 Set Refer Coins", callback_data="admin_set_refer")
    btn_set_vip = types.InlineKeyboardButton("💰 Set VIP Price", callback_data="admin_set_vip_price")
    
    markup.add(btn_pending, btn_stats, btn_block_user, btn_unblock_user, btn_delete_user, btn_set_qr, btn_set_support, btn_set_bonus, btn_set_refer, btn_set_vip)
    
    bot.send_message(
        message.chat.id, 
        f"🔐 **Admin Dashboard:**\n\n"
        f"• Approved Users: `{len(approved_profiles)}`\n"
        f"• Blocked Users: `{len(blocked_users)}`\n"
        f"• Current Daily Bonus: `{bot_settings['daily_bonus_coins']}` Coins\n"
        f"• Current Refer Coins: `{bot_settings['refer_coins']}` Coins\n"
        f"• Current VIP Price: `{bot_settings['vip_price']}`\n\n"
        f"Choose from the options below:", 
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
            bot.send_message(target_id, "🎉 Your profile has been approved. Send /start to view the main menu.")
            try:
                bot.edit_message_caption(chat_id=chat_id, message_id=call.message.message_id, caption=call.message.caption + "\n\n✅ **Approved**", parse_mode="Markdown")
            except Exception:
                pass
        bot.answer_callback_query(call.id, "Profile approved successfully!")

    elif data.startswith("reject_"):
        target_id = int(data.split("_")[1])
        if target_id in pending_profiles:
            pending_profiles.pop(target_id)
            bot.send_message(target_id, "❌ Your information has been rejected. Please try again using /start.")
            try:
                bot.edit_message_caption(chat_id=chat_id, message_id=call.message.message_id, caption=call.message.caption + "\n\n❌ **Rejected**", parse_mode="Markdown")
            except Exception:
                pass
        bot.answer_callback_query(call.id, "Profile rejected.")

    elif data.startswith("admin_block_"):
        target_id = int(data.split("_")[2])
        blocked_users.add(target_id)
        if target_id in approved_profiles:
            approved_profiles.pop(target_id)
        bot.send_message(target_id, "🚫 Your account has been blocked by the admin due to policy violations or a report.")
        bot.answer_callback_query(call.id, f"User {target_id} has been blocked successfully!", show_alert=True)
        try:
            bot.edit_message_reply_markup(chat_id=chat_id, message_id=call.message.message_id, reply_markup=None)
        except Exception:
            pass

    elif data.startswith("admin_delete_"):
        target_id = int(data.split("_")[2])
        if target_id in approved_profiles:
            approved_profiles.pop(target_id)
        if target_id in pending_profiles:
            pending_profiles.pop(target_id)
        bot.send_message(target_id, "🗑️ Your profile has been deleted by the admin.")
        bot.answer_callback_query(call.id, f"User profile {target_id} deleted successfully!", show_alert=True)
        try:
            bot.edit_message_reply_markup(chat_id=chat_id, message_id=call.message.message_id, reply_markup=None)
        except Exception:
            pass

    elif data == "admin_dismiss_report":
        bot.answer_callback_query(call.id, "Report dismissed.")
        try:
            bot.edit_message_reply_markup(chat_id=chat_id, message_id=call.message.message_id, reply_markup=None)
        except Exception:
            pass

    elif data == "admin_pending_list":
        if not pending_profiles:
            bot.answer_callback_query(call.id, "There are no pending profiles.", show_alert=True)
        else:
            bot.answer_callback_query(call.id, f"Total pending profiles: {len(pending_profiles)}", show_alert=True)

    elif data == "admin_stats":
        bot.answer_callback_query(call.id, f"Approved: {len(approved_profiles)} | Pending: {len(pending_profiles)} | Blocked: {len(blocked_users)}", show_alert=True)

    elif data == "admin_block_prompt":
        msg = bot.send_message(chat_id, "Please enter the **Telegram User ID** you want to block:")
        bot.register_next_step_handler(msg, process_block_user_id)

    elif data == "admin_unblock_prompt":
        msg = bot.send_message(chat_id, "Please enter the **Telegram User ID** you want to unblock:")
        bot.register_next_step_handler(msg, process_unblock_user_id)

    elif data == "admin_delete_prompt":
        msg = bot.send_message(chat_id, "Please enter the **Telegram User ID** whose profile you want to delete:")
        bot.register_next_step_handler(msg, process_delete_user_id)

    elif data == "admin_set_qr":
        msg = bot.send_message(chat_id, "Please send the new **UPI QR Code (Photo)**:")
        bot.register_next_step_handler(msg, save_upi_qr)
        
    elif data == "admin_set_support":
        msg = bot.send_message(chat_id, "Please send your new Telegram Username for help/support (e.g., @AdminHelp):")
        bot.register_next_step_handler(msg, save_support_contact)

    elif data == "admin_set_bonus":
        msg = bot.send_message(chat_id, "How many coins do you want to give for the daily bonus? (Enter numbers only, e.g., 15 or 20):")
        bot.register_next_step_handler(msg, save_bonus_amount)

    elif data == "admin_set_refer":
        msg = bot.send_message(chat_id, "How many coins do you want to give per referral? (Enter numbers only, e.g., 50 or 100):")
        bot.register_next_step_handler(msg, save_refer_amount)

    elif data == "admin_set_vip_price":
        msg = bot.send_message(chat_id, "Please enter the new VIP price (e.g., ₹199 or $5):")
        bot.register_next_step_handler(msg, save_vip_price)

def process_block_user_id(message):
    if message.text.isdigit():
        uid = int(message.text)
        blocked_users.add(uid)
        if uid in approved_profiles:
            approved_profiles.pop(uid)
        bot.send_message(message.chat.id, f"✅ User ID `{uid}` has been blocked successfully.", parse_mode="Markdown")
        try:
            bot.send_message(uid, "🚫 Your account has been blocked by the admin.")
        except Exception:
            pass
    else:
        bot.send_message(message.chat.id, "⚠️ Please enter a valid numeric user ID.")

def process_unblock_user_id(message):
    if message.text.isdigit():
        uid = int(message.text)
        if uid in blocked_users:
            blocked_users.remove(uid)
            bot.send_message(message.chat.id, f"✅ User ID `{uid}` has been unblocked successfully.", parse_mode="Markdown")
            try:
                bot.send_message(uid, "🎉 Your account has been unblocked! Send /start to access the bot.")
            except Exception:
                pass
        else:
            bot.send_message(message.chat.id, "⚠️ This user ID is not in the blocked list.")
    else:
        bot.send_message(message.chat.id, "⚠️ Please enter a valid numeric user ID.")

def process_delete_user_id(message):
    if message.text.isdigit():
        uid = int(message.text)
        deleted = False
        if uid in approved_profiles:
            approved_profiles.pop(uid)
            deleted = True
        if uid in pending_profiles:
            pending_profiles.pop(uid)
            deleted = True
        if uid in user_coins:
            user_coins.pop(uid)
            
        if deleted:
            bot.send_message(message.chat.id, f"✅ Profile data for User ID `{uid}` has been completely deleted.", parse_mode="Markdown")
            try:
                bot.send_message(uid, "🗑️ Your profile has been deleted by the admin.")
            except Exception:
                pass
        else:
            bot.send_message(message.chat.id, "⚠️ No profile found with this User ID.")
    else:
        bot.send_message(message.chat.id, "⚠️ Please enter a valid numeric user ID.")

def save_upi_qr(message):
    if message.content_type == 'photo':
        bot_settings["upi_qr_file_id"] = message.photo[-1].file_id
        bot.send_message(message.chat.id, "✅ UPI QR Code updated successfully!")
    else:
        bot.send_message(message.chat.id, "⚠️ Please send a photo only.")

def save_support_contact(message):
    if message.text:
        bot_settings["support_contact"] = message.text
        bot.send_message(message.chat.id, f"✅ Support contact updated to: {message.text}")
    else:
        bot.send_message(message.chat.id, "⚠️ Please send text.")

def save_bonus_amount(message):
    if message.text.isdigit():
        bot_settings["daily_bonus_coins"] = int(message.text)
        bot.send_message(message.chat.id, f"✅ Daily bonus has been updated to `{message.text} Coins`!", parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, "⚠️ Please enter a valid number only.")

def save_refer_amount(message):
    if message.text.isdigit():
        bot_settings["refer_coins"] = int(message.text)
        bot.send_message(message.chat.id, f"✅ Referral reward has been updated to `{message.text} Coins`!", parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, "⚠️ Please enter a valid number only.")

def save_vip_price(message):
    if message.text:
        bot_settings["vip_price"] = message.text
        bot.send_message(message.chat.id, f"✅ VIP price has been updated to `{message.text}`!", parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, "⚠️ Please enter valid text/price.")

# ----------------- User Menu Button Handlers -----------------

@bot.message_handler(func=lambda message: message.text == "🔍 Find Partner")
def find_partner(message):
    if message.chat.id in blocked_users:
        return
    bot.send_message(message.chat.id, "🔍 Searching for the best matches across India for you... Please wait.")

@bot.message_handler(func=lambda message: message.text == "💌 My Matches")
def my_matches(message):
    if message.chat.id in blocked_users:
        return
    bot.send_message(message.chat.id, "💌 Here you will see matches who liked you. (Coming soon!)")

@bot.message_handler(func=lambda message: message.text == "👤 My Profile")
def my_profile(message):
    chat_id = message.chat.id
    if chat_id in blocked_users:
        return
    if chat_id in approved_profiles:
        p = approved_profiles[chat_id]
        coins = user_coins.get(chat_id, 0)
        profile_text = (
            f"👤 **Your Profile Details:**\n\n"
            f"Name: {p['name']}\nAge: {p['age']}\nDistrict/City: {p['district']}\n\n"
            f"💰 **Your Coins:** {coins} Coins"
        )
        bot.send_photo(chat_id, p["selfie"], caption=profile_text, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "🎁 Daily Bonus")
def daily_bonus(message):
    chat_id = message.chat.id
    if chat_id in blocked_users:
        return
    if chat_id in approved_profiles:
        today = str(date.today())
        if last_bonus_date.get(chat_id) == today:
            bot.send_message(chat_id, "⚠️ You have already claimed today's bonus. Please come back tomorrow!")
        else:
            reward = bot_settings["daily_bonus_coins"]
            user_coins[chat_id] = user_coins.get(chat_id, 0) + reward
            last_bonus_date[chat_id] = today
            
            bot.send_message(
                chat_id, 
                f"🎉 **Congratulations!** You have received today's daily bonus.\n\n"
                f"💰 **Received:** +{reward} Coins\n"
                f"💼 **Total Balance:** {user_coins[chat_id]} Coins",
                parse_mode="Markdown"
            )
    else:
        bot.send_message(chat_id, "⚠️ Please get your profile approved first.")

@bot.message_handler(func=lambda message: message.text == "💎 VIP Features")
def vip_features(message):
    chat_id = message.chat.id
    if chat_id in blocked_users:
        return
    vip_price = bot_settings.get("vip_price", "₹199")
    
    vip_text = (
        f"💎 **VIP Membership**\n\n"
        f"💵 **Price:** {vip_price}\n"
        f"☑️ Blue tick on profile\n"
        f"♾️ Unlimited chats and matches\n\n"
        f"**To become VIP, make payment on the QR Code below and send the screenshot to support:**"
    )
    
    if bot_settings.get("upi_qr_file_id"):
        bot.send_photo(chat_id, bot_settings["upi_qr_file_id"], caption=vip_text, parse_mode="Markdown")
    else:
        bot.send_message(chat_id, vip_text + "\n\n*(QR Code is currently not available, please contact support.)*", parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "👥 Refer & Earn")
def invite_friends(message):
    chat_id = message.chat.id
    if chat_id in blocked_users:
        return
    if chat_id in approved_profiles:
        bot_info = bot.get_me()
        refer_link = f"https://t.me/{bot_info.username}?start={chat_id}"
        reward = bot_settings["refer_coins"]
        
        invite_text = (
            f"👥 **Invite & Earn**\n\n"
            f"Share this bot with your friends! When your friend joins using this link, you will instantly get **{reward} Coins**.\n\n"
            f"🔗 **Your Personal Referral Link:**\n`{refer_link}`\n\n"
            f"*(Click the link to copy)*"
        )
        bot.send_message(chat_id, invite_text, parse_mode="Markdown")
    else:
        bot.send_message(chat_id, "⚠️ Please get your profile approved first.")

@bot.message_handler(func=lambda message: message.text == "🚨 Report Issue")
def report_issue(message):
    chat_id = message.chat.id
    if chat_id in blocked_users:
        return
    if chat_id in approved_profiles:
        msg = bot.send_message(chat_id, "🚨 Please describe the issue, bug, or provide the user ID/details you want to report:")
        bot.register_next_step_handler(msg, process_user_report)
    else:
        bot.send_message(chat_id, "⚠️ Please get your profile approved first.")

def process_user_report(message):
    chat_id = message.chat.id
    if chat_id in blocked_users:
        return
    report_text = message.text
    user_info = approved_profiles.get(chat_id, {})
    name = user_info.get('name', 'Unknown')
    
    admin_report_msg = (
        f"🚨 **New User Report:**\n\n"
        f"👤 **From User:** {name}\n"
        f"🆔 **User ID:** `{chat_id}`\n"
        f"📝 **Details:**\n{report_text}"
    )
    
    if ADMIN_ID:
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("🚫 Block User", callback_data=f"admin_block_{chat_id}"),
            types.InlineKeyboardButton("🗑️ Delete Profile", callback_data=f"admin_delete_{chat_id}"),
            types.InlineKeyboardButton("❌ Dismiss Report", callback_data="admin_dismiss_report")
        )
        bot.send_message(ADMIN_ID, admin_report_msg, reply_markup=markup, parse_mode="Markdown")
    
    bot.send_message(chat_id, "✅ Your report has been successfully sent to the admin. Thank you for keeping the community safe!")

@bot.message_handler(func=lambda message: message.text == "🎧 Help / Support")
def help_support(message):
    if message.chat.id in blocked_users:
        return
    support_id = bot_settings.get("support_contact", "@YourAdminUsername")
    bot.send_message(message.chat.id, f"🎧 Contact support for any issues, reports, or payment screenshots:\n\n👉 **{support_id}**", parse_mode="Markdown")

# ----------------- Run Bot & Server -----------------
if __name__ == "__main__":
    keep_alive()
    print("All India Dating Bot started successfully...")
    bot.infinity_polling()
