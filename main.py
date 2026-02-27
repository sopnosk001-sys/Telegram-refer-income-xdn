import os
import json
import time
import random
import logging
import io
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- CONFIGURATION ---
BOT_TOKEN = "8567246060:AAF9Q3lBp__DNRxZ6xz-Xv3mPvbxkV82A4w"
ADMIN_ID = 5810613583
CHANNELS = [
    {"id": -1002383687280, "username": "@XDNLEGACY"},
    {"id": -1003824270566, "username": "@sopnotrader_vip"},
    {"id": -1002068776879, "username": "@SOPNOTrader"}
]
SUPPORT_USER = "@CEO_cryfex"
REFER_REWARD = 0.2
DAILY_BONUS_MIN = 0.1
DAILY_BONUS_MAX = 0.2
MIN_WITHDRAWAL = 1.50
DB_FILE = "bot_database.json"

# --- LOGGING ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# --- DATABASE ---
def load_db():
    if not os.path.exists(DB_FILE):
        return {"users": {}}
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

def get_user(user_id):
    db = load_db()
    user_id = str(user_id)
    if user_id not in db["users"]:
        user_count = len(db["users"]) + 1
        db["users"][user_id] = {
            "balance": 0.0,
            "referrals": 0,
            "referred_by": None,
            "last_bonus": 0,
            "withdrawals": [],
            "user_number": user_count
        }
        save_db(db)
    return db["users"][user_id]

def update_user(user_id, key, value):
    db = load_db()
    user_id = str(user_id)
    if user_id in db["users"]:
        db["users"][user_id][key] = value
        save_db(db)

def add_balance(user_id, amount):
    user = get_user(user_id)
    new_balance = round(user["balance"] + amount, 2)
    update_user(user_id, "balance", new_balance)
    return new_balance

# --- KEYBOARDS ---
def main_menu(is_admin=False):
    keyboard = [
        [KeyboardButton("💰 Balance"), KeyboardButton("👥 Refer & Earn")],
        [KeyboardButton("🎁 Daily Bonus"), KeyboardButton("💸 Withdrawal")],
        [KeyboardButton("👨‍💻 Support")]
    ]
    if is_admin:
        keyboard.append([KeyboardButton("🔐 Admin Panel")])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

def admin_menu():
    keyboard = [
        [KeyboardButton("👤 User Info"), KeyboardButton("💰 Balance Control")],
        [KeyboardButton("📢 Send SMS"), KeyboardButton("⚙️ Withdrawal Set")],
        [KeyboardButton("📥 User Data Download")],
        [KeyboardButton("🔙 Back")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def withdrawal_action_menu(user_id, amount):
    keyboard = [
        [
            InlineKeyboardButton("✅ Confirm", callback_data=f"wd_confirm_{user_id}_{amount}"),
            InlineKeyboardButton("❌ Cancel", callback_data=f"wd_cancel_{user_id}_{amount}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def balance_control_menu():
    keyboard = [
        [KeyboardButton("➕ Add Balance"), KeyboardButton("➖ Remove Balance")],
        [KeyboardButton("🔙 Admin Menu")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def send_sms_menu():
    keyboard = [
        [KeyboardButton("📢 All User"), KeyboardButton("👤 Custom User")],
        [KeyboardButton("🔙 Admin Menu")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def withdraw_menu():
    keyboard = [
        [KeyboardButton("Binance ID")],
        [KeyboardButton("USDT (BEP20)"), KeyboardButton("USDT (TRC20)")],
        [KeyboardButton("🔙 Back")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def cancel_menu():
    keyboard = [[KeyboardButton("❌ Cancel")]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def join_menu(channels):
    keyboard = []
    for ch in channels:
        keyboard.append([InlineKeyboardButton(f"Join {ch['username']}", url=f"https://t.me/{ch['username'][1:]}")])
    keyboard.append([InlineKeyboardButton("✅ Joined", callback_data="check_joined")])
    return InlineKeyboardMarkup(keyboard)

# --- HANDLERS ---
async def check_membership(bot, user_id):
    for channel in CHANNELS:
        try:
            member = await bot.get_chat_member(channel["id"], user_id)
            if member.status in ["left", "kicked"]:
                return False, channel["username"]
        except Exception:
            return False, channel["username"]
    return True, None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user:
        return
    user_id = update.effective_user.id
    db = load_db()
    is_new = str(user_id) not in db["users"]
    user = get_user(user_id)
    
    if is_new:
        admin_msg = (
            f"🆕 *New User Joined!*\n\n"
            f"👤 *Name:* {update.effective_user.full_name}\n"
            f"🆔 *Chat ID:* `{user_id}`\n"
            f"🔢 *User Number:* {user['user_number']}"
        )
        try:
            await context.bot.send_message(chat_id=ADMIN_ID, text=admin_msg, parse_mode="Markdown")
        except:
            pass

    if context.args and user["referred_by"] is None:
        ref_id = context.args[0]
        if ref_id.isdigit() and int(ref_id) != user_id:
            update_user(user_id, "referred_by", int(ref_id))

    is_member, _ = await check_membership(context.bot, user_id)
    if not is_member:
        await update.message.reply_text(
            "🚀 *Welcome to our Professional Bot!*\n\nTo use this bot, you must join our channels first.",
            parse_mode="Markdown",
            reply_markup=join_menu(CHANNELS)
        )
    else:
        await update.message.reply_text(
            f"👋 *Hello {update.effective_user.first_name}!*\n\nWelcome back to the dashboard. Start earning now!",
            parse_mode="Markdown",
            reply_markup=main_menu(user_id == ADMIN_ID)
        )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query or not query.from_user:
        return
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == "check_joined":
        user = get_user(user_id)
        is_member, missing = await check_membership(context.bot, user_id)
        if is_member:
            if user.get("referred_by") and not user.get("referral_rewarded"):
                ref_id = user["referred_by"]
                add_balance(ref_id, REFER_REWARD)
                ref_user = get_user(ref_id)
                update_user(ref_id, "referrals", ref_user["referrals"] + 1)
                update_user(user_id, "referral_rewarded", True)
                
                try:
                    await context.bot.send_message(
                        chat_id=ref_id,
                        text=(
                            f"🎊 *New Referral Notification!*\n\n"
                            f"👤 *User:* {query.from_user.full_name}\n"
                            f"💰 *You Earned:* `{REFER_REWARD}` USDT\n\n"
                            f"Keep sharing your link to earn more!"
                        ),
                        parse_mode="Markdown"
                    )
                except Exception:
                    pass
                
            await query.message.reply_text(
                "✅ *Success!*\n\nYou have joined all channels. Welcome to the bot!",
                parse_mode="Markdown",
                reply_markup=main_menu(user_id == ADMIN_ID)
            )
        else:
            await query.message.reply_text(f"❌ You haven't joined {missing} yet!")

    elif data.startswith("wd_confirm_"):
        parts = data.split("_")
        target_user_id = parts[2]
        amount = parts[3]
        tax_id = f"TAX{random.randint(100000, 999999)}"
        
        db = load_db()
        if target_user_id in db["users"]:
            withdrawals = db["users"][target_user_id].get("withdrawals", [])
            for w in withdrawals:
                if w.get("status") == "Pending" and str(w.get("amount")) == amount:
                    w["status"] = "Confirmed"
                    w["tax_id"] = tax_id
                    break
            save_db(db)
            
            msg = (
                f"✅ *Withdrawal Successful!*\n\n"
                f"💰 *Amount:* `{amount}` USDT\n"
                f"📝 *Tax ID:* `{tax_id}`\n"
                f"Status: Confirmed"
            )
            try:
                await context.bot.send_message(chat_id=target_user_id, text=msg, parse_mode="Markdown")
            except:
                pass
            await query.edit_message_text(f"✅ Withdrawal of {amount} confirmed for {target_user_id}")

    elif data.startswith("wd_cancel_"):
        parts = data.split("_")
        target_user_id = parts[2]
        amount = float(parts[3])
        
        db = load_db()
        if target_user_id in db["users"]:
            withdrawals = db["users"][target_user_id].get("withdrawals", [])
            for w in withdrawals:
                if w.get("status") == "Pending" and w.get("amount") == amount:
                    w["status"] = "Cancelled"
                    break
            save_db(db)
            add_balance(target_user_id, amount) 
            
            try:
                await context.bot.send_message(chat_id=target_user_id, text=f"❌ Your withdrawal of {amount} USDT has been cancelled and refunded.")
            except:
                pass
            await query.edit_message_text(f"❌ Withdrawal of {amount} cancelled for {target_user_id}")

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not update.message:
        return
    user_id = update.effective_user.id
    user = get_user(user_id)
    text = update.message.text
    is_admin = (user_id == ADMIN_ID)

    if "Balance" in text:
        db = load_db()
        user_id_str = str(user_id)
        user_data_db = db["users"].get(user_id_str, {})
        withdrawals = user_data_db.get("withdrawals", [])
        processing_amount = sum(w["amount"] for w in withdrawals if w.get("status") == "Pending")
        msg = (
            f"🏦 *Your Account Balance*\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👤 *Name:* {update.effective_user.full_name}\n"
            f"🆔 *User ID:* `{user_id}`\n\n"
            f"💰 *Balance:* `{user['balance']}` USDT\n"
            f"⏳ *Withdrawal Processing:* `{processing_amount}` USDT\n"
            f"👥 *Total Referrals:* `{user['referrals']}`\n"
            f"━━━━━━━━━━━━━━━━━━"
        )
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=main_menu(is_admin))

    elif "Refer & Earn" in text:
        bot_username = (await context.bot.get_me()).username
        ref_link = f"https://t.me/{bot_username}?start={user_id}"
        msg = (
            f"👥 *Refer & Earn Program*\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"Share your referral link with friends and earn `{REFER_REWARD}` USDT for every active user who joins!\n\n"
            f"🔗 *Your Referral Link:*\n`{ref_link}`\n\n"
            f"📊 *Stats:*\n"
            f"Total Referrals: `{user['referrals']}`\n"
            f"Total Earned: `{round(user['referrals'] * REFER_REWARD, 2)}` USDT\n"
            f"━━━━━━━━━━━━━━━━━━"
        )
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=main_menu(is_admin))

    elif "Daily Bonus" in text:
        now = time.time()
        last_bonus = user.get("last_bonus", 0)
        if now - last_bonus < 12 * 3600:
            remaining = int((12 * 3600) - (now - last_bonus))
            hours = remaining // 3600
            minutes = (remaining % 3600) // 60
            await update.message.reply_text(f"⏳ *Bonus locked!*\n\nPlease wait `{hours}h {minutes}m` to claim again.", parse_mode="Markdown")
        else:
            amount = round(random.uniform(DAILY_BONUS_MIN, DAILY_BONUS_MAX), 2)
            add_balance(user_id, amount)
            update_user(user_id, "last_bonus", now)
            await update.message.reply_text(f"🎁 *Daily Bonus Claimed!*\n\nYou received `{amount}` USDT!", parse_mode="Markdown")

    elif "Withdrawal" in text:
        await update.message.reply_text(
            f"💸 *Withdrawal Portal*\n\nSelect your preferred withdrawal method:",
            parse_mode="Markdown",
            reply_markup=withdraw_menu()
        )

    elif "Support" in text:
        support_user_clean = SUPPORT_USER.replace("@", "")
        support_link = f"https://t.me/{support_user_clean}"
        await update.message.reply_text(
            f"👨‍💻 *Support Center*\n\nIf you have any issues or questions, contact our CEO directly:\n\n👤 *User:* [Contact CEO]({support_link})",
            parse_mode="Markdown",
            reply_markup=main_menu(is_admin)
        )

    elif text == "🔙 Back":
        await update.message.reply_text("👋 *Main Dashboard*", reply_markup=main_menu(is_admin))

    elif text == "🔐 Admin Panel" and is_admin:
        await update.message.reply_text("👮 *Admin Dashboard*", reply_markup=admin_menu())

    elif text == "👤 User Info" and is_admin:
        await update.message.reply_text("🔍 Please enter the User's Chat ID:", reply_markup=ReplyKeyboardRemove())
        context.user_data["admin_action"] = "get_user_info"

    elif text == "💰 Balance Control" and is_admin:
        await update.message.reply_text("💰 Balance Control Menu:", reply_markup=balance_control_menu())

    elif text == "➕ Add Balance" and is_admin:
        await update.message.reply_text("💳 Please enter the User's Chat ID to ADD balance:", reply_markup=ReplyKeyboardRemove())
        context.user_data["admin_action"] = "add_bal_id"

    elif text == "➖ Remove Balance" and is_admin:
        await update.message.reply_text("💳 Please enter the User's Chat ID to REMOVE balance:", reply_markup=ReplyKeyboardRemove())
        context.user_data["admin_action"] = "rem_bal_id"

    elif text == "📢 Send SMS" and is_admin:
        await update.message.reply_text("📢 SMS Broadcasting Menu:", reply_markup=send_sms_menu())

    elif text == "📢 All User" and is_admin:
        await update.message.reply_text("📝 Enter the message to send to ALL users:", reply_markup=ReplyKeyboardRemove())
        context.user_data["admin_action"] = "broadcast_msg"

    elif text == "👤 Custom User" and is_admin:
        await update.message.reply_text("🆔 Enter the User's Chat ID:", reply_markup=ReplyKeyboardRemove())
        context.user_data["admin_action"] = "custom_sms_id"

    elif text == "⚙️ Withdrawal Set" and is_admin:
        await update.message.reply_text("⚙️ Enter new Minimum Withdrawal amount:", reply_markup=ReplyKeyboardRemove())
        context.user_data["admin_action"] = "set_min_withdraw"

    elif text == "📥 User Data Download" and is_admin:
        db = load_db()
        file_content = json.dumps(db, indent=4)
        bio = io.BytesIO(file_content.encode('utf-8'))
        bio.name = "user_data.json"
        await update.message.reply_document(document=bio, caption="📊 All User Data")

    elif text == "🔙 Admin Menu" and is_admin:
        await update.message.reply_text("👮 *Admin Dashboard*", reply_markup=admin_menu())

    elif context.user_data.get("admin_action") == "get_user_info" and is_admin:
        try:
            target_id = text.strip()
            db = load_db()
            if target_id in db["users"]:
                target_user = db["users"][target_id]
                msg = (
                    f"👤 *User Information*\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"🆔 *Chat ID:* `{target_id}`\n"
                    f"💰 *Balance:* `{target_user['balance']}` USDT\n"
                    f"👥 *Referrals:* `{target_user['referrals']}`\n"
                    f"🔢 *User Number:* {target_user.get('user_number', 'N/A')}\n"
                    f"━━━━━━━━━━━━━━━━━━"
                )
                await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=admin_menu())
            else:
                await update.message.reply_text("❌ User not found!", reply_markup=admin_menu())
        except:
            await update.message.reply_text("❌ Error processing request.", reply_markup=admin_menu())
        context.user_data["admin_action"] = None

    elif context.user_data.get("admin_action") == "add_bal_id" and is_admin:
        context.user_data["target_id"] = text.strip()
        await update.message.reply_text("💰 Enter amount to ADD:")
        context.user_data["admin_action"] = "add_bal_amt"

    elif context.user_data.get("admin_action") == "add_bal_amt" and is_admin:
        try:
            amt = float(text)
            target_id = context.user_data.get("target_id")
            add_balance(target_id, amt)
            await update.message.reply_text(f"✅ Added `{amt}` to user `{target_id}`", reply_markup=admin_menu())
        except:
            await update.message.reply_text("❌ Invalid amount.", reply_markup=admin_menu())
        context.user_data["admin_action"] = None

    elif context.user_data.get("admin_action") == "rem_bal_id" and is_admin:
        context.user_data["target_id"] = text.strip()
        await update.message.reply_text("💰 Enter amount to REMOVE:")
        context.user_data["admin_action"] = "rem_bal_amt"

    elif context.user_data.get("admin_action") == "rem_bal_amt" and is_admin:
        try:
            amt = float(text)
            target_id = context.user_data.get("target_id")
            add_balance(target_id, -amt)
            await update.message.reply_text(f"✅ Removed `{amt}` from user `{target_id}`", reply_markup=admin_menu())
        except:
            await update.message.reply_text("❌ Invalid amount.", reply_markup=admin_menu())
        context.user_data["admin_action"] = None

    elif context.user_data.get("admin_action") == "broadcast_msg" and is_admin:
        db = load_db()
        count = 0
        for uid in db["users"]:
            try:
                await context.bot.send_message(chat_id=uid, text=text)
                count += 1
            except:
                pass
        await update.message.reply_text(f"✅ Sent to {count} users.", reply_markup=admin_menu())
        context.user_data["admin_action"] = None

    elif context.user_data.get("admin_action") == "custom_sms_id" and is_admin:
        context.user_data["target_id"] = text.strip()
        await update.message.reply_text("📝 Enter message:")
        context.user_data["admin_action"] = "custom_sms_msg"

    elif context.user_data.get("admin_action") == "custom_sms_msg" and is_admin:
        target_id = context.user_data.get("target_id")
        try:
            await context.bot.send_message(chat_id=target_id, text=text)
            await update.message.reply_text(f"✅ Message sent to `{target_id}`", reply_markup=admin_menu())
        except:
            await update.message.reply_text("❌ Failed to send message.", reply_markup=admin_menu())
        context.user_data["admin_action"] = None

    elif context.user_data.get("admin_action") == "set_min_withdraw" and is_admin:
        try:
            global MIN_WITHDRAWAL
            MIN_WITHDRAWAL = float(text)
            await update.message.reply_text(f"✅ Minimum withdrawal set to `{MIN_WITHDRAWAL}`", reply_markup=admin_menu())
        except:
            await update.message.reply_text("❌ Invalid amount.", reply_markup=admin_menu())
        context.user_data["admin_action"] = None

    elif text in ["Binance ID", "USDT (BEP20)", "USDT (TRC20)"]:
        method = text.replace(" ID", "").replace(" (", "_").replace(")", "").upper()
        context.user_data["wd_method"] = text
        prompt = "Please enter your Binance ID:" if "BINANCE" in method else f"Please enter your {text} Address:"
        await update.message.reply_text(
            f"📝 *Step 1/3*\n\n{prompt}", 
            parse_mode="Markdown",
            reply_markup=cancel_menu()
        )
        context.user_data["awaiting_address"] = True

    elif text == "❌ Cancel":
        context.user_data["awaiting_address"] = False
        context.user_data["awaiting_amount"] = False
        await update.message.reply_text("❌ *Withdrawal Cancelled*", parse_mode="Markdown", reply_markup=main_menu(is_admin))

    elif context.user_data.get("awaiting_address"):
        context.user_data["wd_address"] = text
        context.user_data["awaiting_address"] = False
        context.user_data["awaiting_amount"] = True
        await update.message.reply_text(
            f"📝 *Step 2/3*\n\nEnter the amount to withdraw (Min {MIN_WITHDRAWAL} USDT):", 
            parse_mode="Markdown",
            reply_markup=cancel_menu()
        )
        
    elif context.user_data.get("awaiting_amount"):
        try:
            amount = float(text)
            if amount < MIN_WITHDRAWAL:
                await update.message.reply_text(f"❌ *Minimum withdrawal is {MIN_WITHDRAWAL} USDT*", parse_mode="Markdown")
            elif amount > user["balance"]:
                await update.message.reply_text(f"❌ *Insufficient balance!* Your balance is `{user['balance']}` USDT", parse_mode="Markdown")
            else:
                add_balance(user_id, -amount)
                method = context.user_data.get("wd_method")
                address = context.user_data.get("wd_address")
                
                withdrawals = user.get("withdrawals", [])
                withdrawals.append({"amount": amount, "method": method, "address": address, "time": time.time(), "status": "Pending"})
                update_user(user_id, "withdrawals", withdrawals)
                
                admin_msg = (
                    f"🔔 *New Withdrawal Request*\n\n"
                    f"👤 *User:* {update.effective_user.full_name}\n"
                    f"🆔 *Chat ID:* `{user_id}`\n"
                    f"💰 *Amount:* `{amount}` USDT\n"
                    f"🏦 *Method:* `{method}`\n"
                    f"📍 *Address:* `{address}`"
                )
                await context.bot.send_message(
                    chat_id=ADMIN_ID,
                    text=admin_msg,
                    parse_mode="Markdown",
                    reply_markup=withdrawal_action_menu(user_id, amount)
                )

                await update.message.reply_text(
                    f"✅ *Withdrawal Request Successful!*\n\n"
                    f"💰 *Amount:* `{amount}` USDT\n"
                    f"🏦 *Method:* `{method}`\n"
                    f"📍 *To:* `{address}`\n\n"
                    f"Your request is being processed. Thank you!",
                    parse_mode="Markdown",
                    reply_markup=main_menu(is_admin)
                )
                context.user_data["awaiting_amount"] = False
        except ValueError:
            await update.message.reply_text("❌ Please enter a valid number for the amount.")

# --- MAIN ---
def main():
    if not BOT_TOKEN:
        print("Error: BOT_TOKEN not found.")
        return

    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), message_handler))
    
    print("Bot is starting...")
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
