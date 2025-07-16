
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
INTERVAL = 60
PRICE_HISTORY_FILE = 'price_history.json'

# === ФУНКЦИИ ===
def get_current_price():
    url = f'https://api.coingecko.com/api/v3/simple/price?ids={COIN_ID}&vs_currencies={VS_CURRENCY}'
    try:
        print("[*] Запрашиваю текущую цену с CoinGecko...")
        r = requests.get(url)
        data = r.json()
        print("[+] Ответ от CoinGecko:", data)
        if COIN_ID in data and VS_CURRENCY in data[COIN_ID]:
            return data[COIN_ID][VS_CURRENCY]
        else:
            print("[!] Ошибка в структуре ответа от CoinGecko:", data)
            return None
    except Exception as e:
        print("[!] Ошибка при получении цены:", e)
        return None

def send_alert(message):
    url = f'https://api.telegram.org/bot{TOKEN}/sendMessage'
    payload = {'chat_id': CHAT_ID, 'text': message}
    try:
        print(f"[*] Отправляю сообщение в Telegram: {message}")
        r = requests.post(url, data=payload)
        print("[+] Ответ Telegram API:", r.status_code, r.text)
    except Exception as e:
        print("[!] Ошибка при отправке Telegram-сообщения:", e)

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
    print("[*] Запускаю main() и отправляю тест-сообщение...")
    send_alert("✅ ТЕСТ: Бот успешно запущен и подключён к Telegram.")
    while True:
        print("[*] Проверка цены...")
        current_price = get_current_price()
        if current_price is None:
            print("[!] Цена не получена. Жду...")
            time.sleep(INTERVAL)
            continue

        print(f"[+] Текущая цена ETH: ${current_price}")
        timestamp = datetime.utcnow().isoformat()
        history = load_price_history()
        history.append({'price': current_price, 'timestamp': timestamp})

        cutoff = datetime.utcnow() - timedelta(days=7)
        history = [h for h in history if datetime.fromisoformat(h['timestamp']) > cutoff]

        save_price_history(history)

        prices = [h['price'] for h in history]
        ath = max(prices)
        threshold = ath * 0.999

        print(f"[+] 7-дневный ATH: ${ath:.2f} | Порог (−0.1%): ${threshold:.2f}")

        if current_price <= threshold:
            print("[!] Цена упала ниже порога. Отправляю уведомление...")
            send_alert(f"✅ ТЕСТ: ETH упал на 0.1% от 7-дневного ATH (${ath:.2f} → ${current_price:.2f})")
        else:
            print("[*] Всё в порядке. Жду следующую проверку...")

        time.sleep(INTERVAL)

# === ЗАГЛУШКА ДЛЯ RENDER ===
app = Flask(__name__)

@app.route('/')
def home():
    return "Debug bot is running!"

if __name__ == '__main__':
    print("[*] Flask запускается...")
    threading.Thread(target=main).start()
    app.run(host='0.0.0.0', port=10000)
