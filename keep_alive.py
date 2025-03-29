from flask import Flask
from threading import Thread
import time
import requests

app = Flask('')

@app.route('/')
def home():
    return "✅ Бот активен и работает 24/7!"

def run():
    app.run(host='0.0.0.0', port=8080)

def ping_self():
    while True:
        try:
            requests.get("https://telegrambot.onrender.com")
            print("🔁 Пинг отправлен — бот жив.")
        except:
            print("❌ Пинг не отправлен.")
        time.sleep(300)

def keep_alive():
    Thread(target=run).start()
    Thread(target=ping_self).start()
