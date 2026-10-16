import csv
import io
import random
import re
import requests
import telebot
from telebot import types



# ---------- НАСТРОЙКИ ----------
import os
BOT_TOKEN = os.getenv("TELEGRAM_DWOBOTAI_TOKEN")        
SHEET_ID = "1TpSlkri5eBhNYPMEAPhaXSUqWL7l4bGkU9VibMfYwCw"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# ---------- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ----------
def get_all_rows():
    """Скачивает таблицу и возвращает список строк (каждая строка — список ячеек)."""
    resp = requests.get(CSV_URL, timeout=15)
    resp.raise_for_status()
    # Декодируем и парсим CSV
    content = resp.content.decode("utf-8")
    reader = csv.reader(io.StringIO(content))
    rows = list(reader)
    return rows

def get_random_task():
    """Возвращает случайную строку, кроме первой (заголовка)."""
    rows = get_all_rows()
    if len(rows) <= 1:
        return None
    # Пропускаем первую строку (индекс 0)
    return random.choice(rows[1:])

def find_review_by_number(number: str):
    """Ищет в столбце 7 (индекс 6) текст, содержащий указанный номер."""
    rows = get_all_rows()
    # Пропускаем заголовок
    for row in rows[1:]:
        if len(row) > 6:
            cell = row[6].strip()
            # Ищем номер как отдельное слово или в начале строки
            if re.search(rf'\b{re.escape(number)}\b', cell):
                return cell
    return None

# ---------- КЛАВИАТУРА ----------
def main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_task = types.KeyboardButton("📋 Задание")
    btn_review = types.KeyboardButton("🔍 Ревью")
    markup.add(btn_task, btn_review)
    return markup

# ---------- ОБРАБОТЧИКИ ----------
@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(
        message.chat.id,
        "Привет! Я помогу с заданиями. Выбери действие:",
        reply_markup=main_keyboard()
    )

@bot.message_handler(func=lambda m: m.text == "📋 Задание")
def send_task(message):
    try:
        row = get_random_task()
        if not row:
            bot.send_message(message.chat.id, "⚠️ В таблице нет данных.")
            return
        # Отправляем ячейки с 1 по 6 (индексы 0–5) последовательно
        for i in range(6):
            text = row[i].strip() if i < len(row) else ""
            if text:
                # Отправляем как обычный текст, чтобы не ломать форматирование
                bot.send_message(message.chat.id, text, parse_mode=None)
            else:
                bot.send_message(message.chat.id, "—")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка при чтении таблицы: {e}")

@bot.message_handler(func=lambda m: m.text == "🔍 Ревью")
def ask_review_number(message):
    msg = bot.send_message(
        message.chat.id,
        "Введите номер задания:",
        reply_markup=types.ReplyKeyboardRemove()
    )
    bot.register_next_step_handler(msg, process_review_number)

def process_review_number(message):
    number = message.text.strip()
    try:
        text = find_review_by_number(number)
        if text:
            # Экранируем HTML-спецсимволы, чтобы Telegram не сломал разметку
            safe_text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            # Оборачиваем в <code> для удобного копирования
            bot.send_message(
                message.chat.id,
                f"<code>{safe_text}</code>",
                parse_mode="HTML"
            )
            bot.send_message(
                message.chat.id,
                "Скопируйте промт, загрузите фото с результатом задания в ИИ и вставьте промт. Удачи!"
            )
        else:
            bot.send_message(message.chat.id, "Sorry, нет такого задания")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка: {e}")
    finally:
        # Возвращаем главную клавиатуру
        bot.send_message(message.chat.id, "Выберите действие:", reply_markup=main_keyboard())

# ---------- ЗАПУСК ----------
if __name__ == "__main__":
    print("Бот запущен...")
    bot.infinity_polling()