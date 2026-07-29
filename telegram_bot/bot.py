import os
import time
import json
import io
import requests
import qrcode
from PIL import Image
import telebot
from telebot import types
import database as db

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "7961205315:AAHQvR4w5_2yY_96g3jJ3K6Xw3X-Q9Y-1Z4") # Replace with your token
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))  # Set your Telegram numeric ID or 0 for public admin commands
MASTER_API_KEY = os.getenv("MASTER_API_KEY", "upi_live_087a45b4c6aa8f4d7af201a0e6a53090")
UPSTREAM_HOST = "https://duskyr.com"

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, parse_mode="HTML")

# Helper: Generate QR Image Bytes
def generate_qr_bytes(text):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=3,
    )
    qr.add_data(text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    bio = io.BytesIO()
    img.save(bio, 'PNG')
    bio.seek(0)
    return bio

# User States for multi-step prompts
USER_STEPS = {}

# -------------------------------------------------------------------
# Main Start & Help Handlers
# -------------------------------------------------------------------
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    user_id = message.from_user.id
    active_key = db.get_user_key(user_id)
    key_data = db.get_key_data(active_key) if active_key else None
    credits = key_data.get("credits", 0) if key_data else 0

    status_str = f"🟢 <b>Key Active:</b> <code>{active_key}</code> ({credits} Credits remaining)" if active_key and credits > 0 else "🔴 <b>No Active Key Set</b>"

    welcome_text = (
        f"🤖 <b>Welcome to GPT India UPI Generator Bot!</b>\n\n"
        f"Convert your ChatGPT session tokens directly into instant scannable UPI Payment QR codes.\n\n"
        f"Status: {status_str}\n\n"
        f"⚡ <b>Quick Actions:</b>\n"
        f"• Send your ChatGPT Session JSON to generate a UPI QR link.\n"
        f"• Use <b>Activate Key</b> to set your Customer Key.\n"
        f"• Use <b>Buy Credits</b> to purchase instant credits."
    )

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🔑 Activate Key", callback_data="btn_activate"),
        types.InlineKeyboardButton("⚡ Create UPI QR", callback_data="btn_create_qr"),
        types.InlineKeyboardButton("💳 Buy Credits", callback_data="btn_buy"),
        types.InlineKeyboardButton("📊 My Balance", callback_data="btn_balance"),
    )
    if ADMIN_ID == 0 or user_id == ADMIN_ID:
        markup.add(types.InlineKeyboardButton("👑 Admin Panel", callback_data="btn_admin"))

    bot.send_message(message.chat.id, welcome_text, reply_markup=markup)

# -------------------------------------------------------------------
# Callback Query Handler
# -------------------------------------------------------------------
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id

    if call.data == "btn_activate":
        msg = bot.send_message(chat_id, "🔑 <b>Please enter your Customer License Key:</b>\n(e.g., <code>GPTIND_XXXXXX</code>)")
        bot.register_next_step_handler(msg, process_set_key)

    elif call.data == "btn_create_qr":
        active_key = db.get_user_key(user_id)
        key_data = db.get_key_data(active_key) if active_key else None

        if not active_key or not key_data:
            bot.answer_callback_query(call.id, "Please activate a customer key first!", show_alert=True)
            return

        if key_data.get("credits", 0) <= 0:
            bot.answer_callback_query(call.id, "0 Credits remaining! Please buy credits first.", show_alert=True)
            return

        msg = bot.send_message(chat_id, "⚡ <b>Paste your ChatGPT Session JSON or token:</b>\n<i>(Get it from chatgpt.com/api/auth/session)</i>")
        bot.register_next_step_handler(msg, process_create_qr)

    elif call.data == "btn_balance":
        active_key = db.get_user_key(user_id)
        if not active_key:
            bot.send_message(chat_id, "❌ No active key set. Use /key <YOUR_KEY> to set one.")
            return

        key_data = db.get_key_data(active_key)
        if not key_data:
            bot.send_message(chat_id, "❌ Invalid active key.")
            return

        txt = (
            f"📊 <b>Account Balance</b>\n\n"
            f"🔑 <b>Active Key:</b> <code>{active_key}</code>\n"
            f"💳 <b>Credits Remaining:</b> {key_data.get('credits', 0)}\n"
            f"📈 <b>Total Created:</b> {key_data.get('total_used', 0)} links\n"
            f"📦 <b>Plan:</b> {key_data.get('plan_name', 'Standard')}"
        )
        bot.send_message(chat_id, txt)

    elif call.data == "btn_buy":
        send_plans(chat_id)

    elif call.data == "btn_admin":
        if ADMIN_ID != 0 and user_id != ADMIN_ID:
            bot.answer_callback_query(call.id, "Unauthorized: Admin access required.", show_alert=True)
            return
        send_admin_menu(chat_id)

# -------------------------------------------------------------------
# Key Activation Logic
# -------------------------------------------------------------------
@bot.message_handler(commands=['key'])
def set_key_command(message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        bot.reply_to(message, "Usage: <code>/key GPTIND_XXXXXX</code>")
        return
    process_set_key_text(message, args[1].strip())

def process_set_key(message):
    process_set_key_text(message, message.text.strip())

def process_set_key_text(message, key_str):
    key_str = key_str.upper()
    key_data = db.get_key_data(key_str)
    if not key_data:
        bot.reply_to(message, f"❌ <b>Invalid Customer Key:</b> <code>{key_str}</code>\nPlease verify your key or purchase credits below.")
        return

    db.set_user_key(message.from_user.id, key_str)
    credits = key_data.get("credits", 0)
    bot.reply_to(message, f"🎉 <b>Key Activated Successfully!</b>\n\n🔑 <b>Key:</b> <code>{key_str}</code>\n💳 <b>Credits:</b> {credits}\n\nYou can now send your ChatGPT session to generate QR links!")

# -------------------------------------------------------------------
# QR Creation & Upstream Polling
# -------------------------------------------------------------------
def process_create_qr(message):
    user_id = message.from_user.id
    session_json = message.text.strip() if message.text else ""

    active_key = db.get_user_key(user_id)
    key_data = db.get_key_data(active_key) if active_key else None

    if not active_key or not key_data or key_data.get("credits", 0) <= 0:
        bot.reply_to(message, "❌ Insufficient credits or key expired. Use /key or buy credits.")
        return

    if len(session_json) < 10:
        bot.reply_to(message, "❌ Invalid session input. Please paste your full session JSON or accessToken.")
        return

    # Deduct 1 credit
    success, remaining = db.deduct_credit(active_key)
    if not success:
        bot.reply_to(message, "❌ Insufficient credits!")
        return

    status_msg = bot.reply_to(message, "⏳ <b>Connecting to ChatGPT Gateway...</b>")

    try:
        # Step 1: Upstream Create Order Call
        resp = requests.post(
            f"{UPSTREAM_HOST}/api/upi/v1/create",
            headers={"Authorization": f"Bearer {MASTER_API_KEY}", "Content-Type": "application/json"},
            json={"session_json": session_json},
            timeout=15
        )
        res_json = resp.json()

        if resp.status_code != 200 or not res_json.get("ok"):
            err_msg = res_json.get("message") or res_json.get("error") or "Upstream gateway error"
            db.refund_credit(active_key, "FAIL_CREATE")
            bot.edit_message_text(f"❌ <b>Creation Failed:</b> {err_msg}\n\n✓ Your 1 credit has been refunded.", status_msg.chat.id, status_msg.message_id)
            return

        order_code = res_json.get("order_code")
        payment_url = res_json.get("payment_url")

        if payment_url:
            deliver_qr_result(status_msg.chat.id, status_msg.message_id, payment_url, order_code, active_key)
            return

        # Step 2: Poll Order Status if pending
        poll_order_status(status_msg.chat.id, status_msg.message_id, order_code, active_key)

    except Exception as e:
        db.refund_credit(active_key, "FAIL_EXCEPT")
        bot.edit_message_text(f"❌ <b>Error:</b> {str(e)}\n\n✓ Your 1 credit has been refunded.", status_msg.chat.id, status_msg.message_id)

def poll_order_status(chat_id, message_id, order_code, active_key):
    attempts = 0
    max_attempts = 45 # 90 seconds max

    while attempts < max_attempts:
        attempts += 1
        time.sleep(2)

        if attempts == 3:
            try: bot.edit_message_text("⚙️ <b>Logging into ChatGPT session...</b>", chat_id, message_id)
            except Exception: pass
        elif attempts == 10:
            try: bot.edit_message_text("⚡ <b>Creating UPI Payment Gateway...</b>", chat_id, message_id)
            except Exception: pass
        elif attempts == 20:
            try: bot.edit_message_text("🎨 <b>Finalizing scannable QR code...</b>", chat_id, message_id)
            except Exception: pass

        try:
            resp = requests.get(
                f"{UPSTREAM_HOST}/api/upi/v1/order/{order_code}",
                headers={"Authorization": f"Bearer {MASTER_API_KEY}"},
                timeout=10
            )
            data = resp.json()
            status = data.get("status")
            pay_url = data.get("payment_url") or (data.get("data") and data.get("data").get("payment_url"))

            if pay_url or status in ["completed", "ready", "success"]:
                deliver_qr_result(chat_id, message_id, pay_url, order_code, active_key)
                return

            if status == "failed" or data.get("ok") is False or "error" in data:
                err_reason = data.get("message") or data.get("error") or "Session token expired or rejected."
                db.refund_credit(active_key, order_code)
                bot.edit_message_text(
                    f"❌ <b>Creation Failed</b>\n\nReason: {err_reason}\n\n✓ <b>Your 1 Credit was automatically refunded!</b>",
                    chat_id, message_id
                )
                return

        except Exception:
            pass

    # Timeout
    db.refund_credit(active_key, order_code)
    bot.edit_message_text(
        f"⚠️ <b>Order Timed Out</b>\n\nThe upstream server took too long. Please verify your ChatGPT session token and try again.\n\n✓ <b>Your 1 Credit was refunded!</b>",
        chat_id, message_id
    )

def deliver_qr_result(chat_id, message_id, payment_url, order_code, active_key):
    # Delete loading text message
    try: bot.delete_message(chat_id, message_id)
    except Exception: pass

    # Generate QR Image
    qr_img_bytes = generate_qr_bytes(payment_url)

    key_data = db.get_key_data(active_key)
    rem_credits = key_data.get("credits", 0) if key_data else 0

    caption = (
        f"🎉 <b>ChatGPT Plus UPI QR Code Ready!</b>\n\n"
        f"🆔 <b>Order Code:</b> <code>#{order_code}</code>\n"
        f"💳 <b>Credits Remaining:</b> {rem_credits}\n\n"
        f"📌 <b>Instructions:</b> Scan this QR in GPay / PhonePe / Paytm / BHIM to confirm payment within 5 minutes."
    )

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("⚡ Open Payment Page", url=payment_url)
    )

    bot.send_photo(chat_id, photo=qr_img_bytes, caption=caption, reply_markup=markup)

# Handle raw session JSON text sent directly to bot
@bot.message_handler(func=lambda message: message.text and ("accessToken" in message.text or "{" in message.text))
def direct_session_handler(message):
    process_create_qr(message)

# -------------------------------------------------------------------
# Buy Credits & Plans
# -------------------------------------------------------------------
@bot.message_handler(commands=['buy', 'plans'])
def buy_command(message):
    send_plans(message.chat.id)

def send_plans(chat_id):
    upi_uri = "upi://pay?pa=iamubbb@ibl&pn=GPT%20India&am=350&cu=INR&tn=Credits%20Purchase"
    qr_bytes = generate_qr_bytes(upi_uri)

    plans_text = (
        f"💳 <b>Purchase Customer Credits</b>\n\n"
        f"• <b>Starter Plan:</b> ₹40 for 1 Credit (1 QR Link)\n"
        f"• <b>Pro Saver Plan:</b> ₹350 for 15 Credits (Best Value! ₹23.3 / Link)\n\n"
        f"📌 <b>Pay via UPI:</b>\n"
        f"UPI ID: <code>iamubbb@ibl</code>\n\n"
        f"After paying, send your payment screenshot / UTR to Admin on Telegram to receive your <b>Customer License Key</b>!"
    )

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("⚡ Pay via UPI App", url=upi_uri))

    bot.send_photo(chat_id, photo=qr_bytes, caption=plans_text, reply_markup=markup)

# -------------------------------------------------------------------
# Admin Panel & Commands
# -------------------------------------------------------------------
@bot.message_handler(commands=['admin'])
def admin_command(message):
    if ADMIN_ID != 0 and message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "Unauthorized: Admin access required.")
        return
    send_admin_menu(message.chat.id)

def send_admin_menu(chat_id):
    txt = (
        f"👑 <b>Admin Dashboard</b>\n\n"
        f"<b>Available Admin Commands:</b>\n"
        f"• <code>/genkey &lt;credits&gt;</code> - Generate new key\n"
        f"• <code>/addcredits &lt;key&gt; &lt;amount&gt;</code> - Topup key\n"
        f"• <code>/listkeys</code> - View all keys\n"
        f"• <code>/revoke &lt;key&gt;</code> - Revoke a key"
    )
    bot.send_message(chat_id, txt)

@bot.message_handler(commands=['genkey'])
def genkey_cmd(message):
    if ADMIN_ID != 0 and message.from_user.id != ADMIN_ID: return
    args = message.text.split()
    credits = int(args[1]) if len(args) > 1 else 1
    new_key, key_info = db.generate_key(credits)
    bot.reply_to(message, f"✅ <b>Generated New Customer Key!</b>\n\n🔑 <b>Key:</b> <code>{new_key}</code>\n💳 <b>Credits:</b> {credits}")

@bot.message_handler(commands=['addcredits'])
def addcredits_cmd(message):
    if ADMIN_ID != 0 and message.from_user.id != ADMIN_ID: return
    args = message.text.split()
    if len(args) < 3:
        bot.reply_to(message, "Usage: <code>/addcredits GPTIND_XXXXXX 5</code>")
        return
    target_key = args[1].strip()
    amt = int(args[2])
    new_bal = db.add_credits(target_key, amt)
    bot.reply_to(message, f"✅ <b>Added +{amt} Credits to <code>{target_key}</code></b>\nNew Balance: {new_bal} Credits")

@bot.message_handler(commands=['listkeys'])
def listkeys_cmd(message):
    if ADMIN_ID != 0 and message.from_user.id != ADMIN_ID: return
    keys_map = db.list_all_keys()
    if not keys_map:
        bot.reply_to(message, "No keys found.")
        return
    
    txt = "🔑 <b>Active Customer Keys:</b>\n\n"
    for k, v in list(keys_map.items())[:25]:
        txt += f"• <code>{k}</code> — <b>{v.get('credits',0)} credits</b> (Used: {v.get('total_used',0)})\n"
    bot.send_message(message.chat.id, txt)

@bot.message_handler(commands=['revoke'])
def revoke_cmd(message):
    if ADMIN_ID != 0 and message.from_user.id != ADMIN_ID: return
    args = message.text.split()
    if len(args) < 2: return
    target_key = args[1].strip()
    res = db.revoke_key(target_key)
    bot.reply_to(message, f"Key <code>{target_key}</code> revoked." if res else "Key not found.")

if __name__ == "__main__":
    print("🚀 Starting GPT India UPI Telegram Bot...")
    bot.infinity_polling(skip_pending=True)
