import os
import re
import threading
from flask import Flask, request
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    CommandHandler,
    filters
)
from dotenv import load_dotenv

# === Завантаження токена з .env ===
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
RENDER_HOST = os.getenv("RENDER_EXTERNAL_HOSTNAME")

print(f"BOT_TOKEN: {BOT_TOKEN}")
print(f"RENDER_HOST: {RENDER_HOST}")

# === Словник відмінювання імен ===
name_declensions = {
    "Маша": ("Машу", "female"),
    "Діма": ("Діму", "male"),
    "Саша": ("Сашу", "unisex")
}

# === Дієслова ===
verb_conjugation = {
    "обійняти": ("обійняв", "🤗", "обійняла"),
    "вдарити": ("вдарив", "👊", "вдарила"),
    "поцілувати": ("поцілував", "💋", "поцілувала")
}


def convert_infinitive_to_past(verb, gender="male"):
    forms = verb_conjugation.get(verb.lower())
    if not forms:
        return (verb, "")
    return (forms[0] if gender == "male" else forms[2], forms[1])


def decline_name(name):
    return name_declensions.get(name, (name, "male"))


# === Обробка /start ===
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.first_name
    buttons = [
        [KeyboardButton("ℹ️ Інструкція")],
        [KeyboardButton("💬 Зв’язок з розробником"), KeyboardButton("🔥 Почати рольову дію")],
        [KeyboardButton("📜 Доступні команди")]
    ]
    markup = ReplyKeyboardMarkup(buttons, resize_keyboard=True)
    await update.message.reply_text(
        f"Привіт, {user}! Я ваш рольовий бот 🤖. Використовуйте команди для дій!",
        reply_markup=markup
    )


# === Обробка кастомних команд ===
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

    if message_text:
        response = f'✨ {user_name} {past_verb} {target_display} зі словами: "{message_text}"'
    else:
        response = f'✨ {user_name} {past_verb} {target_display}'

    await update.message.reply_text(response, parse_mode="Markdown")


# === Обробка кнопок ===
async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "ℹ️ Інструкція":
        await update.message.reply_text("Використання: `/дія @Ім'я текст`\nПриклад: `/обійняти @Маша Ти неймовірна!`", parse_mode="Markdown")
    elif text == "💬 Зв’язок з розробником":
        await update.message.reply_text("Розробник: @shadow_tar")
    elif text == "🔥 Почати рольову дію":
        await update.message.reply_text("Додайте мене в чат: https://t.me/BugaichyBot?startgroup=botstart")
    elif text == "📜 Доступні команди":
        await update.message.reply_text("\n".join(verb_conjugation.keys()), parse_mode="Markdown")


# === Flask App для Render Webhook ===
flask_app = Flask(__name__)


@flask_app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.update_queue.put_nowait(update)
    return "ok"


@flask_app.route("/")
def index():
    return "🤖 Бот працює через webhook!"


# === Запуск Telegram Application ===
application = ApplicationBuilder().token(BOT_TOKEN).build()
application.add_handler(CommandHandler("start", start_command))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^/'), handle_command))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_buttons))


# === Старт всього ===
async def on_startup(app):
    url = f"https://{RENDER_HOST}/{BOT_TOKEN}"
    await app.bot.set_webhook(url)
    print(f"✅ Webhook встановлено: {url}")


if __name__ == "__main__":
    print("🤖 Бот запускається...")

    # Запускаємо Flask у окремому потоці
    threading.Thread(target=lambda: flask_app.run(host="0.0.0.0", port=8080)).start()

    # Telegram bot з webhook
    application.run_webhook(
        listen="0.0.0.0",
        port=8080,
        webhook_url=f"https://{RENDER_HOST}/{BOT_TOKEN}",
        post_init=on_startup
    )
