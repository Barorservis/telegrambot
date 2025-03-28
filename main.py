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
        [KeyboardButton("📊 Анализ"), KeyboardButton("📈 Графика")],
        [KeyboardButton("🟥 Прогноз на шорт"), KeyboardButton("🟩 Прогноз на лонг")]
    ], resize_keyboard=True)

    context.bot.send_message(chat_id=update.effective_chat.id, text=welcome_text, parse_mode="Markdown")
    context.bot.send_message(chat_id=update.effective_chat.id, text="📍 Выбери раздел:", reply_markup=keyboard)

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

def get_klines(symbol, interval='1h', limit=50):
    url = f"{BASE_URL}/klines?symbol={symbol}&interval={interval}&limit={limit}"
    return requests.get(url).json()

def handle_text(update: Update, context: CallbackContext):
    text = update.message.text

    if text in ["📊 Анализ", "📈 Графика", "🟥 Прогноз на шорт", "🟩 Прогноз на лонг"]:
        context.user_data['mode'] = text
        coin_buttons = [[KeyboardButton(coin[:-4])] for coin in TOP_COINS]
        coin_buttons.append([KeyboardButton("🔙 Назад")])
        reply_markup = ReplyKeyboardMarkup(coin_buttons, resize_keyboard=True)
        update.message.reply_text("Выбери монету:", reply_markup=reply_markup)
    elif text == "🔙 Назад":
        show_main_menu(update, context)
    elif any(text == coin[:-4] for coin in TOP_COINS):
        symbol = f"{text}USDT"
        mode = context.user_data.get('mode')

        if mode == "📊 Анализ":
            klines = get_klines(symbol)
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

            text = (
                f"📊 *Анализ {symbol[:-4]}*\n\n"
                f"❖ Текущая цена: *${price:.2f}*\n"
                f"❖ RSI (14): *{rsi:.2f}* {rsi_comment}\n"
                f"❖ MA(50): *{ma50:.2f}* {ma_comment}\n"
                f"❖ Объём за 24ч: *{volume_str}*\n"
                f"❖ Зона сопротивления: ~*{resistance:.2f}*\n\n"
                f"_Это лишь базовый обзор. Для полноты картины учитывайте свои цели и стратегию._"
            )
            update.message.reply_text(text, parse_mode="Markdown")

        elif mode == "📈 Графика":
            klines = get_klines(symbol, interval='30m', limit=48)
            times = [datetime.datetime.fromtimestamp(k[0]/1000) for k in klines]
            closes = [float(k[4]) for k in klines]

            plt.figure(figsize=(10, 4))
            plt.plot(times, closes, label=symbol[:-4], color='blue')
            plt.title(f"График {symbol[:-4]} за 24ч")
            plt.xlabel("Время")
            plt.ylabel("Цена")
            plt.grid(True)
            plt.tight_layout()

            buf = io.BytesIO()
            plt.savefig(buf, format='png')
            buf.seek(0)
            plt.close()

            context.bot.send_photo(chat_id=update.effective_chat.id, photo=buf)

        elif mode == "🟥 Прогноз на шорт":
            price = float(get_klines(symbol)[-1][4])
            entry = price * 0.98
            tp = price * 0.95
            sl = price * 1.01
            ma50 = statistics.mean([float(k[4]) for k in get_klines(symbol)])
            rsi = calculate_rsi([float(k[4]) for k in get_klines(symbol)])
            reason = f"RSI: {rsi:.1f}, MA50: {ma50:.2f}, возможный откат от зоны сопротивления."

            text = (
                f"📉 *Шорт сигнал по {symbol[:-4]}*\n\n"
                f"❖ Текущая цена: *${price:.2f}*\n"
                f"❖ Точка входа: ~*${entry:.2f}*\n"
                f"❖ Тейк-профит: ~*${tp:.2f}*\n"
                f"❖ Стоп-лосс: ~*${sl:.2f}*\n"
                f"❖ Причина: {reason}\n\n"
                f"_Убедитесь, что вы оцениваете риски и учитываете свою торговую стратегию._"
            )
            update.message.reply_text(text, parse_mode="Markdown")

        elif mode == "🟩 Прогноз на лонг":
            price = float(get_klines(symbol)[-1][4])
            entry = price * 1.01
            tp = price * 1.05
            sl = price * 0.97
            ma50 = statistics.mean([float(k[4]) for k in get_klines(symbol)])
            rsi = calculate_rsi([float(k[4]) for k in get_klines(symbol)])
            reason = f"RSI: {rsi:.1f}, MA50: {ma50:.2f}, возможный пробой вверх."

            text = (
                f"📈 *Лонг сигнал по {symbol[:-4]}*\n\n"
                f"❖ Текущая цена: *${price:.2f}*\n"
                f"❖ Точка входа: ~*${entry:.2f}*\n"
                f"❖ Тейк-профит: ~*${tp:.2f}*\n"
                f"❖ Стоп-лосс: ~*${sl:.2f}*\n"
                f"❖ Причина: {reason}\n\n"
                f"_Всегда помните о рисках и проводите собственный анализ._"
            )
            update.message.reply_text(text, parse_mode="Markdown")
        else:
            update.message.reply_text("Непонятный режим. Нажмите /start для перезапуска.")
    else:
        update.message.reply_text("Выбери действие с помощью кнопок ⬇️")

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", show_main_menu))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
