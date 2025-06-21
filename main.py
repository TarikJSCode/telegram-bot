import os
import re
import threading
from dotenv import load_dotenv
from flask import Flask, request

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# === Загрузка токена з .env ===
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
RENDER_HOST = os.getenv("RENDER_EXTERNAL_HOSTNAME")
WEBHOOK_PATH = f"/{BOT_TOKEN}"
WEBHOOK_URL = f"https://{RENDER_HOST}{WEBHOOK_PATH}"

# === Flask app ===
flask_app = Flask(__name__)

@flask_app.route("/", methods=["GET"])
def index():
    return "Bot is alive!"

@flask_app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.update_queue.put_nowait(update)
    return "ok", 200

# === Словники ===
name_declensions = {}
verb_conjugation = {}

def convert_infinitive_to_past(verb: str, gender: str = "male") -> tuple[str, str]:
    forms = verb_conjugation.get(verb.lower())
    if not forms:
        return (verb, "")
    return (forms[0] if gender == "male" else forms[2], forms[1])

def decline_name(name: str) -> tuple[str, str]:
    return name_declensions.get(name, (name, "male"))

# === Хендлери ===
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.first_name
    buttons = [
        [KeyboardButton("ℹ️ Інструкція")],
        [KeyboardButton("💬 Зв’язок з розробником"), KeyboardButton("🔥 Почати рольову дію")],
        [KeyboardButton("📜 Доступні команди")]
    ]
    markup = ReplyKeyboardMarkup(buttons, resize_keyboard=True)
    await update.message.reply_text(f"Привіт, {user}! Я ваш рольовий бот 🤖.", reply_markup=markup)

async def handle_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    text = update.message.text.strip()
    user_name = update.effective_user.first_name

    match = re.match(r'^/([\w\sітаією]+?)\s+@(\S+)(?:\s+(.+))?', text, re.IGNORECASE)
    if not match:
        await update.message.reply_text("⚠️ Формат:\n/дія @Ім'я [текст]")
        return

    action_input = match.group(1).strip()
    target_raw = match.group(2).lstrip("@").strip()
    message_text = match.group(3) or ""

    target_name_accusative, gender = decline_name(target_raw)
    past_verb, emoji = convert_infinitive_to_past(action_input, gender)
    target_display = f"{emoji} *{target_name_accusative}*" if emoji else f"*{target_name_accusative}*"

    response = f'✨ {user_name} {past_verb} {target_display}'
    if message_text:
        response += f' зі словами: "{message_text}"'

    await update.message.reply_text(response, parse_mode="Markdown")

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "ℹ️ Інструкція":
        await update.message.reply_text("Використання: `/дія @Ім'я текст`", parse_mode="Markdown")
    elif text == "💬 Зв’язок з розробником":
        await update.message.reply_text("Розробник: @shadow_tar")
    elif text == "🔥 Почати рольову дію":
        await update.message.reply_text("Додайте мене в чат: https://t.me/BugaichyBot?startgroup=botstart")
    elif text == "📜 Доступні команди":
        await update.message.reply_text("Список команд скоро буде додано.", parse_mode="Markdown")

# === Створення Telegram Application ===
application = ApplicationBuilder().token(BOT_TOKEN).build()
application.add_handler(CommandHandler("start", start_command))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^/'), handle_command))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_buttons))

# === Flask запускається окремо ===
def run_flask():
    flask_app.run(host="0.0.0.0", port=8080)

threading.Thread(target=run_flask).start()

# === Webhook встановлення ===
import asyncio
async def setup_webhook():
    await application.bot.set_webhook(WEBHOOK_URL)
    print(f"✅ Webhook встановлено: {WEBHOOK_URL}")

asyncio.run(setup_webhook())
