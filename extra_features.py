import time
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup

admin_state = {}
withdraw_state = {}

def setup_features(bot, users, set_setting, get_setting, ADMIN_ID):

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

    @bot.message_handler(commands=['wallet'])
    def wallet(msg):
        user = users.find_one({"user_id": msg.from_user.id})
        bot.send_message(
            msg.chat.id,
            f"💰 Wallet\n👥 Referrals: {user.get('ref_count',0)}\n💎 Balance: ₹{user.get('balance',0)}",
            parse_mode="HTML"
        )

    @bot.message_handler(commands=['withdraw'])
    def withdraw(msg):
        withdraw_state[msg.from_user.id] = True
        bot.send_message(msg.chat.id, "💸 Send UPI ID or QR")

    @bot.message_handler(commands=['broadcast'])
    def broadcast_cmd(msg):
        if msg.from_user.id == ADMIN_ID:
            admin_state[msg.from_user.id] = "broadcast"
            bot.send_message(msg.chat.id, "📢 Send message")

    @bot.message_handler(commands=['leaderboard'])
    def leaderboard(msg):
        top_users = users.find().sort("ref_count", -1).limit(10)
        text = "🏆 TOP REFERRERS\n\n"
        rank = 1

        for user in top_users:
            text += f"{rank}. @{user.get('username','NoName')} - {user.get('ref_count',0)} 👥\n"
            rank += 1

        bot.send_message(msg.chat.id, text)

    @bot.message_handler(func=lambda msg: msg.text in [
        "💰 Earn Money","👥 Refer & Earn","💎 Wallet","📤 Withdraw","🏆 Leaderboard"
    ])
    def button_handler(msg):

        user_id = msg.from_user.id
        update_user(user_id, msg.from_user.username)

        if msg.text == "👥 Refer & Earn":
            link = f"https://t.me/{bot.get_me().username}?start={user_id}"
            bot.send_message(msg.chat.id, f"👥 Invite Link:\n{link}")

        elif msg.text == "💎 Wallet":
            user = users.find_one({"user_id": user_id})
            bot.send_message(msg.chat.id,
                f"💰 Wallet\n👥 Ref: {user.get('ref_count',0)}\n💎 ₹{user.get('balance',0)}"
            )

        elif msg.text == "📤 Withdraw":
            withdraw_state[user_id] = True
            bot.send_message(msg.chat.id, "💸 Send UPI or QR")

        elif msg.text == "🏆 Leaderboard":
            top_users = users.find().sort("ref_count", -1).limit(10)
            text = "🏆 TOP REFERRERS\n\n"
            for i, u in enumerate(top_users, 1):
                text += f"{i}. {u.get('ref_count',0)} referrals\n"
            bot.send_message(msg.chat.id, text)

        elif msg.text == "💰 Earn Money":
            bot.send_message(msg.chat.id, "💰 Invite users & earn money!")

    @bot.message_handler(content_types=['text','photo','video'])
    def handle_all(msg):

        user_id = msg.from_user.id
        update_user(user_id, msg.from_user.username)

        # ================= ADMIN BROADCAST =================
        if admin_state.get(user_id) == "broadcast":
            admin_state.pop(user_id, None)

            for user in users.find():
                try:
                    bot.copy_message(user["user_id"], msg.chat.id, msg.message_id)
                except:
                    pass

            bot.send_message(msg.chat.id, "✅ Broadcast Done")
            return

        # ================= WITHDRAW =================
        if withdraw_state.get(user_id):

            user = users.find_one({"user_id": user_id})
            balance = user.get("balance", 0)

            if balance < 10:
                bot.send_message(user_id, "❌ Min ₹10 required")
                withdraw_state.pop(user_id, None)
                return

            withdraw_state.pop(user_id, None)

            withdraw_data = msg.text if msg.content_type == "text" else msg.photo[-1].file_id

            users.update_one(
                {"user_id": user_id},
                {"$set": {
                    "withdraw_status": "pending",
                    "withdraw_data": withdraw_data
                }}
            )

            kb = InlineKeyboardMarkup()
            kb.add(
                InlineKeyboardButton("✅ Pay Done", callback_data=f"pay_{user_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"wreject_{user_id}")
            )

            bot.send_message(ADMIN_ID,
                f"💸 Withdraw Request\nUser: {user_id}\n₹{balance}",
                reply_markup=kb
            )

            bot.send_message(user_id, "⏳ Request Sent")
            return

        # ================= PAYMENT PROOF =================
        if msg.content_type == "photo":
            kb = InlineKeyboardMarkup()
            kb.add(
                InlineKeyboardButton("✅ Approve", callback_data=f"approve_{user_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"reject_{user_id}")
            )

            bot.send_photo(
                ADMIN_ID,
                msg.photo[-1].file_id,
                caption=f"💰 Payment Request\nUser: {user_id}",
                reply_markup=kb
            )

            bot.send_message(user_id, "⏳ Payment Under Review")
            return
