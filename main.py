import os
import threading
from flask import Flask
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import requests
import statistics
import matplotlib.pyplot as plt
import io
import datetime
import matplotlib

matplotlib.use('Agg')  # Чтоб не требовать GUI для отрисовки

TOKEN = "8107581760:AAFfGWDdZsA9Npn2oNLQB-OgMNHbeIxfAKI"
CMC_API_KEY = "1bda7385-c9e8-4119-a1aa-1d89aabb96a2"
BASE_URL = "https://api.binance.com/api/v3"

FAKE_USERS_FILE = "fake_users.txt"

app = Flask(__name__)

@app.route('/')
def index():
    return "Bot is running!"

def load_fake_users():
    if os.path.exists(FAKE_USERS_FILE):
        with open(FAKE_USERS_FILE, "r") as f:
            return int(f.read())
    return 9000

def save_fake_users(count):
    with open(FAKE_USERS_FILE, "w") as f:
        f.write(str(count))

def get_cmc_data(symbol):
    """
    Запрашивает данные о монетах на CoinMarketCap
    и возвращает словарь с ключами:
    price, market_cap, volume_24h, percent_change_24h
    или None, если монета не найдена / произошла ошибка.
    """
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
        print(f"CMC Error: {e}", flush=True)
    return None

def get_klines(symbol, interval='1h', limit=50):
    """
    Запрашивает данные свечей на Binance.
    Возвращает список klines или None при ошибке.
    """
    url = f"{BASE_URL}/klines?symbol={symbol}&interval={interval}&limit={limit}"
    try:
        response = requests.get(url)
        data = response.json()
        if isinstance(data, dict) and data.get("code"):
            # Binance вернула ошибку, например { "code": -1121, "msg": "Invalid symbol." }
            raise ValueError(f"Binance error: {data}")
        return data
    except Exception as e:
        print(f"Binance API error: {e}", flush=True)
        return None

def calculate_rsi(closes, period=14):
    """
    Расчёт RSI (14) по закрытиям свечей.
    Если данных меньше, чем period+1, возвращаем 0.
    """
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
        # Добавляем к тикеру 'USDT', чтобы искать монету на Binance
        symbol = f"{text}USDT"

        if mode == "📊 АНАЛИЗ":
            try:
                # 1. Получаем данные с CoinMarketCap
                cmc_data = get_cmc_data(text)
                if cmc_data is None:
                    update.message.reply_text("Данные по монете не найдены в CoinMarketCap.")
                    return

                # 2. Получаем свечи с Binance
                klines = get_klines(symbol)
                if not klines or len(klines) == 0:
                    update.message.reply_text("Монета не найдена на Binance.")
                    return

                closes = [float(k[4]) for k in klines]
                volumes = [float(k[5]) for k in klines]

                # Для MA(50) нужно минимум 50 значений
                if len(closes) < 50:
                    update.message.reply_text("Недостаточно данных для расчёта MA(50).")
                    return

                price = closes[-1]
                ma50 = statistics.mean(closes[-50:])
                rsi = calculate_rsi(closes)
                volume_24h = sum(volumes[-24:])

                # Для сопротивления берём максимум за последние 10 свечей
                if len(closes) < 10:
                    resistance = price
                else:
                    resistance = max(closes[-10:])

                volume_str = f"{volume_24h/1_000_000_000:.2f}B" if volume_24h >= 1e9 else f"{volume_24h/1_000_000:.2f}M"

                # Комментарии к RSI
                rsi_comment = "(норма)"
                if rsi > 70:
                    rsi_comment = "(перекуплен, возможна коррекция вниз)"
                elif rsi < 30:
                    rsi_comment = "(перепродан, возможен отскок вверх)"

                # Комментарии к MA(50)
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
                # Выводим текст ошибки и в лог, и в сообщение бота
                print(f"Анализ ошибка: {e}", flush=True)
                update.message.reply_text(f"Ошибка анализа: {e}\nВозможно, монета не торгуется на Binance.")

        elif mode == "📈 ГРАФИКА":
            try:
                klines = get_klines(symbol, interval='30m', limit=48)
                if not klines or len(klines) == 0:
                    update.message.reply_text("Монета не найдена на Binance (нет данных для графика).")
                    return

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
            except Exception as e:
                print(f"График ошибка: {e}", flush=True)
                update.message.reply_text(f"Ошибка: {e}. Возможно, монета не торгуется на Binance.")
    else:
        update.message.reply_text("Выбери действие с помощью кнопок ⬇️")

def run_bot():
    """
    Функция для запуска Telegram-бота в режиме polling.
    """
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", show_main_menu))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    # Запускаем бота в отдельном потоке
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()

    # Запускаем Flask-приложение, чтобы Render не убивал сервис
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
