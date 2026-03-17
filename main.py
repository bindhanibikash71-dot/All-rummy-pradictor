import os
import random
import threading
from flask import Flask
import telebot
from telebot import types
from openai import OpenAI

# 1. Environment Variables (Set these on Render.com)
BOT_TOKEN = os.environ.get('bot_token')
HF_TOKEN = os.environ.get('hf_token')

# Configuration
CHANNEL_ID = "@silkroad105"  # Your channel username
INSTA_URL = "https://www.instagram.com/arshux._?igsh=MXhndmhlMnY5Zm83bQ=="
TELEGRAM_URL = "https://t.me/silkroad105"

# 2. Initialize Clients
bot = telebot.TeleBot(BOT_TOKEN)
client = OpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key=HF_TOKEN,
)

# 3. Flask Server for Render (Keeps the bot alive)
app = Flask(__name__)

@app.route('/')
def home():
    return "Mines Bot is Online!"

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

# --- Helper Logic ---

def is_user_joined(user_id):
    """Check if user is a member of the required channel."""
    try:
        member = bot.get_chat_member(CHANNEL_ID, user_id)
        if member.status in ['member', 'administrator', 'creator']:
            return True
        return False
    except Exception:
        return False

def get_force_join_markup():
    """Inline buttons for social links and verification."""
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_insta = types.InlineKeyboardButton("📸 Follow Instagram", url=INSTA_URL)
    btn_tele = types.InlineKeyboardButton("📢 Join Telegram", url=TELEGRAM_URL)
    btn_verify = types.InlineKeyboardButton("✅ Verify Membership", callback_data="verify_user")
    markup.add(btn_insta, btn_tele)
    markup.add(btn_verify)
    return markup

def show_main_menu(chat_id):
    """Main keyboard after verification."""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton('💣 Generate Signal'))
    bot.send_message(chat_id, "✅ Access Granted!\nClick the button below to get your Mines signal.", reply_markup=markup)

# --- Bot Handlers ---

# 1. Block Group Chats
@bot.message_handler(func=lambda message: message.chat.type != 'private')
def block_groups(message):
    bot.reply_to(message, "❌ This bot is only available in Private Chat for security reasons.")

# 2. Start Command
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    
    if is_user_joined(user_id):
        show_main_menu(message.chat.id)
    else:
        welcome_text = (
            f"👋 Hello {message.from_user.first_name}!\n\n"
            "To use the Mines AI Predictor, you must complete these steps:\n\n"
            "1️⃣ Follow our Instagram\n"
            "2️⃣ Join our Telegram Channel\n"
            "3️⃣ Click the **Verify** button below."
        )
        bot.send_message(message.chat.id, welcome_text, reply_markup=get_force_join_markup())

# 3. Handle Verify Button Callback
@bot.callback_query_handler(func=lambda call: call.data == "verify_user")
def verify_callback(call):
    if is_user_joined(call.from_user.id):
        bot.answer_callback_query(call.id, "✅ Verified! Welcome.")
        bot.delete_message(call.message.chat.id, call.message.message_id)
        show_main_menu(call.message.chat.id)
    else:
        bot.answer_callback_query(call.id, "❌ Access Denied! Join the channel first.", show_alert=True)

# 4. Handle Mines Signal Generation
@bot.message_handler(func=lambda message: message.text == '💣 Generate Signal')
def handle_prediction(message):
    # Security re-check
    if not is_user_joined(message.from_user.id):
        bot.reply_to(message, "⚠️ You left the channel! Please join again to use the bot.", reply_markup=get_force_join_markup())
        return

    wait_msg = bot.reply_to(message, "🤖 **AI is analyzing the grid...**")
    
    # Generate 5x5 Mines Grid
    grid = ["⬛"] * 25
    stars = random.sample(range(25), 5) # 5 star spots
    for s in stars:
        grid[s] = "⭐"
    
    rows = [grid[i:i+5] for i in range(0, 25, 5)]
    grid_display = "\n".join([" ".join(row) for row in rows])

    # AI Quote from DeepSeek
    try:
        completion = client.chat.completions.create(
            model="deepseek-ai/DeepSeek-R1:novita",
            messages=[{"role": "user", "content": "Give a 1-sentence lucky tip for a player."}],
            max_tokens=40
        )
        ai_tip = completion.choices[0].message.content
    except:
        ai_tip = "Play smart and stay disciplined!"

    final_response = (
        f"🎯 **MINES PREDICTION**\n\n"
        f"{grid_display}\n\n"
        f"💡 **AI Tip:** `{ai_tip}`\n\n"
        f"🕒 *Signal expires in 2 minutes.*"
    )
    
    bot.edit_message_text(final_response, message.chat.id, wait_msg.message_id, parse_mode="Markdown")

# --- Execution ---
if __name__ == "__main__":
    # Start Flask in background
    threading.Thread(target=run_flask).start()
    print("Bot is starting...")
    bot.infinity_polling()
