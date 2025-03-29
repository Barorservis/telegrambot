from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import requests
import statistics
import matplotlib.pyplot as plt
import io
import datetime
import matplotlib
import os
from flask import Flask

matplotlib.use('Agg')

TOKEN = "8107581760:AAFfGWDdZsA9Npn2oNLQB-OgMNHbeIxfAKI"
CMC_API_KEY = "1bda7385-c9e8-4119-a1aa-1d89aabb96a2"
BASE_URL = "https://api.binance.com/api/v3"

FAKE_USERS_FILE = "fake_users.txt"

# Flask приложение для Render
app = Flask(__name__)

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
    params = {"start": "1", "limit": "200", "convert": "USD"}
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

def get_klines(symbol, interval='1h', limit=50):
    url = f"{BASE_URL}/klines?symbol={symbol}&interval={interval}&limit={limit}"
    response = requests.get(url)
    try:
        data = response.json()
        if isinstance(data, dict) and data.get("code"):
            raise ValueError("Binance error: invalid symbol")
        return data
    except Exception as e:
        print(f"Binance API error: {e}")
        return None

def calculate_rsi(closes, period=14):
    if len(closes) < period + 1:
        return 0
    deltas = [closes[i+1] - closes[i] for i in range(len(closes)-1)]
    gains = [delta for delta in deltas if delta > 0]
    losses = [-delta for delta in deltas if delta < 0]
    avg_gain = sum(gains[-period:]) / period if gains else 0.0001
    avg_loss = sum(losses[-period:]) / period if losses else 0.0001
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def show_main_menu(update: Update, context: CallbackContext):
    user = update.effective_user
    first_name = user.first_name or "друг"
    fake_count = load_fake_users() + 1
    save_fake_users(fake_count)

    welcome_text = (
        f"Привет, {first_name}! 👋\n"
        f"TradingZone Бота уже используют {fake_count} человек(а)\n"
        "Этот Telegram-бот проводит реальный технический и фундаментальный анализ любой криптомонеты!\n"
        "[Присоединяйся к нашему сообществу](https://t.me/tradingzone13)"
    )

    keyboard = ReplyKeyboardMarkup([
        [KeyboardButton("📊 Анализ"), KeyboardButton("📈 Графика")]
    ], resize_keyboard=True)

    context.bot.send_message(chat_id=update.effective_chat.id, text=welcome_text, parse_mode="Markdown")
    context.bot.send_message(chat_id=update.effective_chat.id, text="📍 Выбери раздел:", reply_markup=keyboard)

def handle_text(update: Update, context: CallbackContext):
    text = update.message.text.upper()
    mode = context.user_data.get('mode')

    if text in ["📊 АНАЛИЗ", "📈 ГРАФИКА"]:
        context.user_data['mode'] = text
        update.message.reply_text("Введи тикер монеты (например: BTC, ETH, DOGE):")
    elif mode in ["📊 АНАЛИЗ", "📈 ГРАФИКА"]:
        symbol = f"{text}USDT"

        if mode == "📊 АНАЛИЗ":
            try:
                cmc_data = get_cmc_data(text)
                if not cmc_data:
                    update.message.reply_text("Данные по монете не найдены в CoinMarketCap.")
                klines = get_klines(symbol)
                if not klines:
                    update.message.reply_text("Монета не найдена на Binance.")
                    return

                closes = [float(k[4]) for k in klines]
                volumes = [float(k[5]) for k in klines]
                price = closes[-1]
                ma50 = statistics.mean(closes[-50:])
                rsi = calculate_rsi(closes)
                volume_24h = sum(volumes[-24:])
                resistance = max(closes[-10:])
                volume_str = f"{volume_24h/1_000_000_000:.2f}B" if volume_24h >= 1e9 else f"{volume_24h/1_000_000:.2f}M"

                rsi_comment = "(норма)"
                if rsi > 70:
                    rsi_comment = "(перекуплен, возможна коррекция вниз)"
                elif rsi < 30:
                    rsi_comment = "(перепродан, возможен отскок вверх)"

                ma_comment = "(флэт)"
                if price > ma50:
                    ma_comment = "(восходящий тренд)"
                elif price < ma50:
                    ma_comment = "(нисходящий тренд)"

                response = (
                    f"📊 *Анализ {text} (CoinMarketCap)*\n"
                    f"\n❖ Цена: *${cmc_data['price']:.6f}*"
                    f"\n❖ Рыночная капитализация: *${cmc_data['market_cap'] / 1e9:.2f}B*"
                    f"\n❖ Объём за 24ч: *${cmc_data['volume_24h'] / 1e6:.2f}M*"
                    f"\n❖ Изменение за 24ч: *{cmc_data['percent_change_24h']:.2f}%*"
                    f"\n\n📈 *Технический анализ (Binance)*\n"
                    f"\n❖ RSI (14): *{rsi:.2f}* {rsi_comment}"
                    f"\n❖ MA(50): *{ma50:.6f}* {ma_comment}"
                    f"\n❖ Объём за 24ч: *{volume_str}*"
                    f"\n❖ Зона сопротивления: ~*{resistance:.6f}*"
                    f"\n\n_Это лишь базовый обзор. Для полноты картины учитывайте свои цели и стратегию._"
                )

                update.message.reply_text(response, parse_mode="Markdown")

            except Exception as e:
                print(f"Анализ ошибка: {e}")
                update.message.reply_text("Ошибка анализа. Возможно, монета не торгуется на Binance.")

        elif mode == "📈 ГРАФИКА":
            try:
                klines = get_klines(symbol, interval='30m', limit=48)
                times = [datetime.datetime.fromtimestamp(k[0]/1000) for k in klines]
                closes = [float(k[4]) for k in klines]

                plt.figure(figsize=(10, 4))
                plt.plot(times, closes, label=text, color='blue')
                plt.title(f"График {text} за 24ч")
                plt.xlabel("Время")
                plt.ylabel("Цена")
                plt.grid(True)
                plt.tight_layout()

                buf = io.BytesIO()
                plt.savefig(buf, format='png')
                buf.seek(0)
                plt.close()

                context.bot.send_photo(chat_id=update.effective_chat.id, photo=buf)
            except:
                update.message.reply_text("Ошибка: график не доступен. Возможно, монета не торгуется на Binance.")
    else:
        update.message.reply_text("Выбери действие с помощью кнопок ⬇️")

def main():
    # Запуск Flask с указанием порта для Render
    port = int(os.environ.get('PORT', 5000))

    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", show_main_menu))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))

    updater.start_polling()
    updater.idle()

    app.run(host='0.0.0.0', port=port)

# Запуск убран, чтобы избежать дублирующего polling от Render
# if __name__ == '__main__':
#     main()
