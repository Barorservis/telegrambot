from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import requests
import statistics
import matplotlib.pyplot as plt
import io
import datetime
import matplotlib
import os

matplotlib.use('Agg')

TOKEN = os.getenv("BOT_TOKEN")
CMC_API_KEY = "1bda7385-c9e8-4119-a1aa-1d89aabb96a2"
BASE_URL = "https://api.binance.com/api/v3"
TOP_COINS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "AVAXUSDT", "ADAUSDT", "BNBUSDT", "LTCUSDT", "XRPUSDT", "NOTUSDT", "DOGEUSDT"]

FAKE_USERS_FILE = "fake_users.txt"

def load_fake_users():
    if os.path.exists(FAKE_USERS_FILE):
        with open(FAKE_USERS_FILE, "r") as f:
            return int(f.read())
    return 9000

def save_fake_users(count):
    with open(FAKE_USERS_FILE, "w") as f:
        f.write(str(count))

def get_cmc_data(symbol):
    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"
    headers = {"X-CMC_PRO_API_KEY": CMC_API_KEY}
    params = {"start": "1", "limit": "100", "convert": "USD"}
    try:
        response = requests.get(url, headers=headers, params=params)
        data = response.json()["data"]
        for coin in data:
            if coin["symbol"].upper() == symbol.upper():
                return {
                    "price": coin["quote"]["USD"]["price"],
                    "market_cap": coin["quote"]["USD"]["market_cap"],
                    "volume_24h": coin["quote"]["USD"]["volume_24h"],
                    "percent_change_24h": coin["quote"]["USD"]["percent_change_24h"]
                }
    except Exception as e:
        print(f"CMC Error: {e}")
    return None

def show_main_menu(update: Update, context: CallbackContext):
    user = update.effective_user
    first_name = user.first_name or "друг"

    fake_count = load_fake_users() + 1
    save_fake_users(fake_count)

    welcome_text = (
        f"Привет, {first_name}! 👋\n"
        f"TradingZone Бота уже используют {fake_count} человек(а)\n"
        "Этот Telegram-бот, который проводит реальный технический анализ по 10 топ-альтам и также дает прогнозы: Short и Long с точкой входа!\n"
        "[Присоединяйся к нашему сообществу](https://t.me/tradingzone13)"
    )

    keyboard = ReplyKeyboardMarkup([
        [KeyboardButton("📊 Анализ"), KeyboardButton("📈 Графика")]
    ], resize_keyboard=True)

    context.bot.send_message(chat_id=update.effective_chat.id, text=welcome_text, parse_mode="Markdown")
    context.bot.send_message(chat_id=update.effective_chat.id, text="📍 Выбери раздел:", reply_markup=keyboard)

# Остальная часть кода остаётся без изменений, обработчики для шортов и лонгов просто больше не вызываются.

# ... (всё остальное как есть)

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", show_main_menu))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
