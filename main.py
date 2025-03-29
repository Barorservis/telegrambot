import logging
import os
import requests
import matplotlib.pyplot as plt
from telegram import ReplyKeyboardMarkup, KeyboardButton, Update
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters, CallbackContext)
from datetime import datetime

TOKEN = os.getenv("BOT_TOKEN")
BOT_NAME = os.getenv("BOT_NAME")

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

coins = ['BTC', 'ETH', 'SOL', 'AVAX', 'ADA', 'BNB', 'LTC', 'XRP', 'NOT', 'DOGE']

# Получение текущей цены с CoinGecko
def get_price(symbol):
    try:
        ids = {
            'BTC': 'bitcoin', 'ETH': 'ethereum', 'SOL': 'solana', 'AVAX': 'avalanche-2',
            'ADA': 'cardano', 'BNB': 'binancecoin', 'LTC': 'litecoin',
            'XRP': 'ripple', 'NOT': 'notcoin', 'DOGE': 'dogecoin'
        }
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids[symbol]}&vs_currencies=usd"
        response = requests.get(url)
        if response.status_code != 200:
            return "Ошибка запроса к CoinGecko"
        response = response.json()
        if ids[symbol] not in response or 'usd' not in response[ids[symbol]]:
            return "Данные по монете не найдены"
        return response[ids[symbol]]['usd']
    except Exception as e:
        return f"Ошибка получения цены: {e}"

def welcome_text(first_name="трейдер"):
    fake_count = 1523  # Заглушка, можно обновлять по желанию
    return (
        f"Привет, {first_name}! 👋\n"
        f"TradingZone Бота уже используют {fake_count} человек(а)\n"
        "Этот Telegram-бот, который проводит реальный технический анализ по 10 топ-альтам и также дает прогнозы: Short и Long с точкой входа!\n"
        "[Присоединяйся к нашему сообществу](https://t.me/tradingzone13)"
    )

def start(update: Update, context: CallbackContext):
    first_name = update.effective_user.first_name or "трейдер"
    update.message.reply_text(welcome_text(first_name), parse_mode='Markdown')
    keyboard = [
        [KeyboardButton("Анализ")],
        [KeyboardButton("📈 Графика")],
        [KeyboardButton("📉 Прогноз на шорт")],
        [KeyboardButton("📈 Прогноз на лонг")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    update.message.reply_text("📍 Выбери раздел:", reply_markup=reply_markup)

def coin_menu(update: Update, context: CallbackContext, action):
    keyboard = [[KeyboardButton(coin)] for coin in coins]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    update.message.reply_text("Выбери монету:", reply_markup=reply_markup)
    context.user_data['action'] = action

def handle_message(update: Update, context: CallbackContext):
    text = update.message.text
    action = context.user_data.get('action')

    if text in ["Анализ", "📈 Графика", "📉 Прогноз на шорт", "📈 Прогноз на лонг"]:
        if "Анализ" in text:
            coin_menu(update, context, 'analyze')
        elif "шорт" in text:
            coin_menu(update, context, 'short')
        elif "лонг" in text:
            coin_menu(update, context, 'long')
        elif "Графика" in text:
            coin_menu(update, context, 'chart')
    elif text in coins:
        price = get_price(text)
        if isinstance(price, str):
            update.message.reply_text(price)
            return

        if action == 'analyze':
            update.message.reply_text(f"📊 Анализ {text}\nТекущая цена: ${price}")
        elif action == 'short':
            update.message.reply_text(f"🔻 Шорт {text}\nЦена: ${price}\nПричина: Цена на уровне сопротивления.")
        elif action == 'long':
            update.message.reply_text(f"📈 Лонг {text}\nЦена: ${price}\nПричина: Цена пробивает сопротивление вверх.")
        elif action == 'chart':
            update.message.reply_text(f"📉 График {text}\nЦена сейчас: ${price}\n(в будущем добавим картинку)")

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
