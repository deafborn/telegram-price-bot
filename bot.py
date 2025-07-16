
import requests
import time
from datetime import datetime, timedelta
import json
from flask import Flask
import threading

# === НАСТРОЙКИ ===
TOKEN = '7590115389:AAGrbXxzt58py7cNmFhBtsWQKRT2e8Ai20s'
CHAT_ID = '2135324647'
COIN_ID = 'ethereum'
VS_CURRENCY = 'usd'
INTERVAL = 300
PRICE_HISTORY_FILE = 'price_history.json'

# === ФУНКЦИИ ===
def get_current_price():
    url = f'https://api.coingecko.com/api/v3/simple/price?ids={COIN_ID}&vs_currencies={VS_CURRENCY}'
    try:
        r = requests.get(url)
        data = r.json()
        if COIN_ID in data and VS_CURRENCY in data[COIN_ID]:
            return data[COIN_ID][VS_CURRENCY]
        else:
            print("[!] CoinGecko API returned invalid data:", data)
            return None
    except Exception as e:
        print("[!] Error fetching price:", e)
        return None

def send_alert(message):
    url = f'https://api.telegram.org/bot{TOKEN}/sendMessage'
    try:
        requests.post(url, data={'chat_id': CHAT_ID, 'text': message})
    except Exception as e:
        print("[!] Error sending Telegram alert:", e)

def load_price_history():
    try:
        with open(PRICE_HISTORY_FILE, 'r') as f:
            return json.load(f)
    except:
        return []

def save_price_history(history):
    with open(PRICE_HISTORY_FILE, 'w') as f:
        json.dump(history, f)

def main():
    alerted_levels = set()
    while True:
        current_price = get_current_price()
        if current_price is None:
            time.sleep(INTERVAL)
            continue

        timestamp = datetime.utcnow().isoformat()
        history = load_price_history()
        history.append({'price': current_price, 'timestamp': timestamp})

        cutoff = datetime.utcnow() - timedelta(days=7)
        history = [h for h in history if datetime.fromisoformat(h['timestamp']) > cutoff]

        save_price_history(history)

        prices = [h['price'] for h in history]
        ath = max(prices)

        for drop in [10, 20, 30]:
            threshold = ath * (1 - drop / 100)
            if current_price <= threshold and drop not in alerted_levels:
                send_alert(f"⚠️ {COIN_ID.upper()} упал на {drop}% от 7-дневного ATH (${ath:.2f} → ${current_price:.2f})")
                alerted_levels.add(drop)

        if current_price > ath * 0.95:
            alerted_levels.clear()

        time.sleep(INTERVAL)

# === ЗАГЛУШКА ДЛЯ RENDER ===
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

if __name__ == '__main__':
    threading.Thread(target=main).start()
    app.run(host='0.0.0.0', port=10000)
