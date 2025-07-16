import requests
import threading
import time
import json
from datetime import datetime, timedelta, timezone
from flask import Flask

# === Настройки ===
TELEGRAM_TOKEN = '7590115389:AAGrbXxzt58py7cNmFhBtsWQKRT2e8Ai20s'
CHAT_ID = '2135324647'
VS_CURRENCY = 'usd'
COINS = {
    'ethereum': {
        'name': 'Ethereum',
        'history_file': 'price_history_eth.json',
        'alert_flags': {10: False, 20: False, 30: False}
    },
    'bitcoin': {
        'name': 'Bitcoin',
        'history_file': 'price_history_btc.json',
        'alert_flags': {10: False, 20: False, 30: False}
    }
}

# === Telegram ===
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    r = requests.post(url, json=payload)
    print(f"[Telegram] {r.status_code} {r.text}")

# === Работа с ценами ===
def fetch_price(coin_id):
    url = f"https://api.coingecko.com/api/v3/simple/price"
    params = {"ids": coin_id, "vs_currencies": VS_CURRENCY}
    r = requests.get(url)
    data = r.json()
    return data.get(coin_id, {}).get(VS_CURRENCY)

def load_price_history(filename):
    if Path(filename).exists():
        with open(filename, 'r') as f:
            return json.load(f)
    return []

def save_price_history(filename, history):
    with open(filename, 'w') as f:
        json.dump(history, f)

def prune_history(history):
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    return [entry for entry in history if datetime.fromisoformat(entry['timestamp']) > cutoff]

def process_coin(coin_id, config):
    price = fetch_price(coin_id)
    if not price:
        print(f"[!] Не удалось получить цену для {coin_id}")
        return

    now = datetime.now(timezone.utc).isoformat()
    print(f"[{config['name']}] Цена: {price} USD")

    history = load_price_history(config['history_file'])
    history.append({'timestamp': now, 'price': price})
    history = prune_history(history)
    save_price_history(config['history_file'], history)

    ath = max(p['price'] for p in history)
    drawdown = round(100 * (ath - price) / ath, 2)

    print(f"[{config['name']}] 7D ATH: {ath}, Просадка: {drawdown}%")

    for level in [10, 20, 30]:
        if drawdown >= level and not config['alert_flags'][level]:
            send_telegram_message(f"🔻 {config['name']} упал на {level}% от 7-дневного пика
💰 Сейчас: {price} USD
📈 Пик: {ath} USD")
            config['alert_flags'][level] = True
        elif drawdown < level and config['alert_flags'][level]:
            config['alert_flags'][level] = False  # Сбросить, если цена восстановилась

# === Цикл обновления ===
def main():
    send_telegram_message("✅ Бот запущен и отслеживает ETH и BTC")
    while True:
        for coin_id, config in COINS.items():
            try:
                process_coin(coin_id, config)
            except Exception as e:
                print(f"[{coin_id}] Ошибка: {e}")
        time.sleep(300)  # обновление каждые 5 минут

# === Flask (для Render) ===
app = Flask(__name__)
@app.route('/')
def index():
    return "Crypto Price Alert Bot is running."

if __name__ == "__main__":
    print("[*] Flask запускается...")
    threading.Thread(target=main).start()
    app.run(host='0.0.0.0', port=10000)
