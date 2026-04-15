import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import qrcode
from io import BytesIO

from config import TOKEN, ADMIN_ID
from db import add_user, set_setting, get_setting, get_all_users, users

from extra_features import setup_features   # ✅ CONNECT

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# ✅ IMPORTANT: EXTRA FEATURES CONNECT
setup_features(bot, users, set_setting, get_setting, int(ADMIN_ID))

admin_wait = {}
offer_price = {}
pending_screenshot = {}


# =========================
# STORE
# =========================
def get_store():
    old = get_setting("premium", "")
    if old:
        set_setting("premium_link", old)
    return {
        "upi": get_setting("upi", ""),
        "demo": get_setting("demo", ""),
        "price": get_setting("price", "0"),
        "name": get_setting("name", ""),
        "premium_link": get_setting("premium_link", ""),
        "start_text": get_setting("start_text", ""),
        "photo": get_setting("photo", None),
        "sales": int(get_setting("sales", "0")),
        "revenue": int(get_setting("revenue", "0")),
    }


# =========================
# START
# =========================
@bot.message_handler(commands=["start"])
def start(message):
    store = get_store()
    add_user(message.chat.id)

    text = store["start_text"] if store["start_text"] else "Welcome!"

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("💳 BUY PREMIUM", callback_data="buy"))
    kb.add(InlineKeyboardButton("🎬 DEMO", url=store["demo"]))

    photo = store.get("photo")

    if photo:
        try:
            bot.send_photo(message.chat.id, photo, caption=text, reply_markup=kb)
        except:
            bot.send_message(message.chat.id, text, reply_markup=kb)
    else:
        bot.send_message(message.chat.id, text, reply_markup=kb)


# =========================
# ADMIN PANEL
# =========================
@bot.message_handler(commands=["admin"])
def admin_panel(message):
    if int(message.chat.id) != int(ADMIN_ID):
        return

    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("✏ SET NAME", callback_data="set_name"))
    kb.add(InlineKeyboardButton("💰 SET PRICE", callback_data="set_price"))
    kb.add(InlineKeyboardButton("🏦 SET UPI", callback_data="set_upi"))
    kb.add(InlineKeyboardButton("🎬 SET DEMO", callback_data="set_demo"))
    kb.add(InlineKeyboardButton("🔗 SET PREMIUM LINK", callback_data="set_premium"))
    kb.add(InlineKeyboardButton("🖼 SET PHOTO", callback_data="set_photo"))
    kb.add(InlineKeyboardButton("✏ SET START TEXT", callback_data="set_start_text"))
    kb.add(InlineKeyboardButton("👥 USERS", callback_data="users"))
    kb.add(InlineKeyboardButton("📊 STATS", callback_data="stats"))

    bot.send_message(message.chat.id, "👑 ADMIN PANEL", reply_markup=kb)


# =========================
# ADMIN SET
# =========================
@bot.callback_query_handler(func=lambda c: c.data.startswith("set_"))
def admin_set(c):
    if int(c.from_user.id) != int(ADMIN_ID):
        return

    admin_wait[c.from_user.id] = c.data.replace("set_", "")
    bot.send_message(c.message.chat.id, "✏ Send value now:")


# =========================
# 🔥 FIXED HANDLER (NO CONFLICT)
# =========================
@bot.message_handler(func=lambda m: m.from_user.id in admin_wait or pending_screenshot.get(m.from_user.id), content_types=['text', 'photo'])
def handle_all(m):

    user_id = m.from_user.id

    # ADMIN UPDATE
    if user_id in admin_wait:
        action = admin_wait[user_id]

        if action == "photo":
            if m.photo:
                set_setting("photo", m.photo[-1].file_id)
                bot.send_message(m.chat.id, "🖼 PHOTO UPDATED")
            admin_wait.pop(user_id, None)
            return

        if m.text:
            set_setting(action, m.text)
            bot.send_message(m.chat.id, "✅ UPDATED")

        admin_wait.pop(user_id, None)
        return

    # SCREENSHOT
    if pending_screenshot.get(user_id):

        if not m.photo:
            bot.send_message(m.chat.id, "📸 Please send screenshot")
            return

        pending_screenshot.pop(user_id, None)

        kb = InlineKeyboardMarkup()
        kb.add(
            InlineKeyboardButton("✅ APPROVE", callback_data=f"approve_{user_id}"),
            InlineKeyboardButton("❌ REJECT", callback_data=f"reject_{user_id}")
        )

        bot.send_photo(
            ADMIN_ID,
            m.photo[-1].file_id,
            caption=f"💰 PAYMENT PROOF\nUser: {user_id}",
            reply_markup=kb
        )

        bot.send_message(user_id, "⏳ Verification in progress...")


# =========================
# BUY FLOW (SAME)
# =========================
@bot.callback_query_handler(func=lambda c: c.data == "buy")
def buy(c):
    store = get_store()
    price = offer_price.get(c.from_user.id, int(store["price"]))

    qr_link = f"upi://pay?pa={store['upi']}&am={price}&cu=INR"

    qr = qrcode.make(qr_link)
    bio = BytesIO()
    qr.save(bio, "PNG")
    bio.seek(0)

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("💳 I HAVE PAID", callback_data="paid"))
    kb.add(InlineKeyboardButton("❌ CANCEL ORDER", callback_data="cancel"))

    bot.send_photo(c.message.chat.id, bio, caption="💰 Pay & send screenshot", reply_markup=kb)


# बाकी code SAME रहने दो (approve, reject, stats etc.)

print("Bot Running...")
bot.infinity_polling(skip_pending=True, timeout=60, long_polling_timeout=60)
