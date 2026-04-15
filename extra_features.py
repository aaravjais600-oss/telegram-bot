import time
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

admin_state = {}
withdraw_state = {}

def setup_features(bot, users, set_setting, get_setting, ADMIN_ID):

    # =========================
    # USER SAVE + TRACK
    # =========================
    def update_user(user_id, username):
        if not users.find_one({"user_id": user_id}):
            users.insert_one({
                "user_id": user_id,
                "username": username,
                "balance": 0,
                "ref_count": 0,
                "vip": False,
                "last_active": time.time()
            })
        else:
            users.update_one(
                {"user_id": user_id},
                {"$set": {"last_active": time.time()}}
            )

    # =========================
    # MENU BUTTON SYSTEM
    # =========================
    def user_menu():
        kb = ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add("💰 Earn Money", "👥 Refer & Earn")
        kb.add("💎 Wallet", "📤 Withdraw")
        kb.add("🏆 Leaderboard")
        return kb

    @bot.message_handler(commands=['menu'])
    def menu(msg):
        update_user(msg.from_user.id, msg.from_user.username)
        bot.send_message(msg.chat.id, "💎 Earning Panel Open", reply_markup=user_menu())

    # =========================
    # WALLET
    # =========================
    @bot.message_handler(commands=['wallet'])
    def wallet(msg):
        user = users.find_one({"user_id": msg.from_user.id})
        balance = user.get("balance", 0)
        refs = user.get("ref_count", 0)

        text = f"""
💰 <b>YOUR WALLET</b>

👥 Referrals: {refs}
💎 Balance: ₹{balance}
"""
        bot.send_message(msg.chat.id, text, parse_mode="HTML")

    # =========================
    # WITHDRAW
    # =========================
    @bot.message_handler(commands=['withdraw'])
    def withdraw(msg):
        withdraw_state[msg.from_user.id] = True
        bot.send_message(msg.chat.id, "💸 Send UPI ID or QR")

    # =========================
    # BROADCAST
    # =========================
    @bot.message_handler(commands=['broadcast'])
    def broadcast_cmd(msg):
        if msg.from_user.id == ADMIN_ID:
            admin_state[msg.from_user.id] = "broadcast"
            bot.send_message(msg.chat.id, "📢 Send message")

    # =========================
    # PAYMENT REQUEST (VIP)
    # =========================
    @bot.message_handler(commands=['pay'])
    def pay_cmd(msg):
        bot.send_message(msg.chat.id, "💰 Send payment screenshot")

    # =========================
    # LEADERBOARD COMMAND
    # =========================
    @bot.message_handler(commands=['leaderboard'])
    def leaderboard(msg):

        top_users = users.find().sort("ref_count", -1).limit(10)

        text = "🏆 <b>TOP REFERRERS</b>\n\n"

        rank = 1
        for user in top_users:
            username = user.get("username") or "NoName"
            refs = user.get("ref_count", 0)

            text += f"{rank}. @{username} - {refs} 👥\n"
            rank += 1

        bot.send_message(msg.chat.id, text, parse_mode="HTML")

    # =========================
    # BUTTON HANDLER
    # =========================
    @bot.message_handler(func=lambda msg: msg.text in [
        "💰 Earn Money","👥 Refer & Earn","💎 Wallet","📤 Withdraw","🏆 Leaderboard"
    ])
    def button_handler(msg):

        user_id = msg.from_user.id
        update_user(user_id, msg.from_user.username)

        if msg.text == "👥 Refer & Earn":
            # ✅ FIXED referral link
            link = f"https://t.me/{bot.get_me().username}?start={user_id}"
            bot.send_message(msg.chat.id, f"👥 Invite & Earn\n\n🔗 {link}")

        elif msg.text == "💎 Wallet":
            user = users.find_one({"user_id": user_id})
            bot.send_message(
                msg.chat.id,
                f"💰 Wallet\n\n👥 Referrals: {user.get('ref_count',0)}\n💎 Balance: ₹{user.get('balance',0)}"
            )

        elif msg.text == "📤 Withdraw":
            withdraw_state[user_id] = True
            bot.send_message(msg.chat.id, "💸 Send UPI ID or QR")

        elif msg.text == "🏆 Leaderboard":
            top_users = users.find().sort("ref_count", -1).limit(10)

            text = "🏆 TOP REFERRERS\n\n"
            rank = 1

            for user in top_users:
                text += f"{rank}. {user.get('ref_count',0)} referrals\n"
                rank += 1

            bot.send_message(msg.chat.id, text)

        elif msg.text == "💰 Earn Money":
            bot.send_message(msg.chat.id, "💰 Invite users & earn money!")

    # =========================
    # HANDLE ALL
    # =========================
    @bot.message_handler(content_types=['text','photo','video'])
    def handle_all(msg):

        user_id = msg.from_user.id
        update_user(user_id, msg.from_user.username)

        if admin_state.get(user_id) == "broadcast":
            for user in users.find():
                try:
                    bot.copy_message(user["user_id"], msg.chat.id, msg.message_id)
                except Exception as e:   # ✅ FIXED
                    print(e)
            bot.send_message(msg.chat.id, "✅ Broadcast Done")
            admin_state.pop(user_id)
            return

        if withdraw_state.get(user_id):
            user = users.find_one({"user_id": user_id})
            balance = user.get("balance", 0)

            if balance < 10:
                bot.send_message(user_id, "❌ Min ₹10 required")
                withdraw_state.pop(user_id)
                return

            # ✅ FIXED QR / text save
            withdraw_data = msg.text if msg.content_type == "text" else msg.photo[-1].file_id

            users.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "withdraw_status": "pending",
                        "withdraw_data": withdraw_data
                    }
                }
            )

            kb = InlineKeyboardMarkup()
            kb.add(
                InlineKeyboardButton("✅ Pay Done", callback_data=f"pay_{user_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"wreject_{user_id}")
            )

            bot.send_message(ADMIN_ID, f"💸 Withdraw Request\nUser: {user_id}\n₹{balance}", reply_markup=kb)
            bot.send_message(user_id, "⏳ Request Sent")
            withdraw_state.pop(user_id)
            return

        if msg.content_type == "photo":
            kb = InlineKeyboardMarkup()
            kb.add(
                InlineKeyboardButton("✅ Approve", callback_data=f"approve_{user_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"reject_{user_id}")
            )

            bot.send_photo(ADMIN_ID, msg.photo[-1].file_id,
                caption=f"💰 Payment Request\nUser: {user_id}",
                reply_markup=kb)

            bot.send_message(user_id, "⏳ Payment Under Review")
