import logging
import os
import requests
import matplotlib.pyplot as plt
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (Updater, CommandHandler, CallbackQueryHandler,
                          MessageHandler, Filters, CallbackContext)
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

def welcome_text():
    first_name = "трейдер"  # По умолчанию, можно заменить на update.effective_user.first_name внутри handler-а
    fake_count = 1523  # Заглушка, можно обновлять по желанию
    return (
        f"Привет, {first_name}! 👋
"
        f"TradingZone Бота уже используют {fake_count} человек(а)
"
        "Этот Telegram-бот, который проводит реальный технический анализ по 10 топ-альтам и также дает прогнозы: Short и Long с точкой входа!
"
        "[Присоединяйся к нашему сообществу](https://t.me/tradingzone13)"
    )

def start(update: Update, context: CallbackContext):
    update.message.reply_text(welcome_text())
    keyboard = [
        [InlineKeyboardButton("Анализ", callback_data='analyze')],
        [InlineKeyboardButton("📈 Графика", callback_data='chart')],
        [InlineKeyboardButton("📉 Прогноз на шорт", callback_data='short')],
        [InlineKeyboardButton("📈 Прогноз на лонг", callback_data='long')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("📍 Выбери раздел:", reply_markup=reply_markup)

def crypto_buttons(update: Update, context: CallbackContext, action):
    keyboard = [[InlineKeyboardButton(coin, callback_data=f'{action}_{coin}')] for coin in coins]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.callback_query.edit_message_text(f"Выбери монету:", reply_markup=reply_markup)

def handle_coin_action(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    data = query.data
    action, coin = data.split('_')

    price = get_price(coin)
    if isinstance(price, str):
        query.edit_message_text(price)
        return

    if action == 'analyze':
        query.edit_message_text(f"📊 Анализ {coin}\nТекущая цена: ${price}")
    elif action == 'short':
        query.edit_message_text(f"🔻 Шорт {coin}\nЦена: ${price}\nПричина: Цена на уровне сопротивления.")
    elif action == 'long':
        query.edit_message_text(f"📈 Лонг {coin}\nЦена: ${price}\nПричина: Цена пробивает сопротивление вверх.")
    elif action == 'chart':
        query.edit_message_text(f"📉 График {coin}\nЦена сейчас: ${price}\n(в будущем добавим картинку)")

def button(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    if query.data == 'analyze':
        crypto_buttons(update, context, 'analyze')
    elif query.data == 'short':
        crypto_buttons(update, context, 'short')
    elif query.data == 'long':
        crypto_buttons(update, context, 'long')
    elif query.data == 'chart':
        crypto_buttons(update, context, 'chart')
    elif '_' in query.data:
        handle_coin_action(update, context)

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CallbackQueryHandler(button))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
