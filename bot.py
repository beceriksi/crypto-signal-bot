import requests
import pandas as pd
import numpy as np
import time
import datetime
import os

# === TELEGRAM BİLGİLERİ ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# === BİNANCE API ===
BASE_URL = "https://api.binance.com/api/v3/klines"

# === ANALİZ FONKSİYONU ===
def get_klines(symbol, interval="1h", limit=100):
    url = f"{BASE_URL}?symbol={symbol}&interval={interval}&limit={limit}"
    data = requests.get(url).json()
    df = pd.DataFrame(data, columns=[
        'time','open','high','low','close','volume','close_time',
        'qav','num_trades','taker_base_vol','taker_quote_vol','ignore'
    ])
    df['close'] = df['close'].astype(float)
    df['volume'] = df['volume'].astype(float)
    return df

def check_signal(symbol):
    df = get_klines(symbol)
    df['EMA20'] = df['close'].ewm(span=20).mean()
    df['EMA50'] = df['close'].ewm(span=50).mean()

    delta = df['close'].diff()
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)
    avg_gain = pd.Series(gain).rolling(window=14).mean()
    avg_loss = pd.Series(loss).rolling(window=14).mean()
    rs = avg_gain / avg_loss
    df['RSI'] = 100 - (100 / (1 + rs))

    df['vol_mean'] = df['volume'].rolling(window=10).mean()

    last = df.iloc[-1]
    if (
        last['EMA20'] > last['EMA50']
        and 30 < last['RSI'] < 50
        and last['volume'] > last['vol_mean']
    ):
        return True, last['RSI'], last['volume'] / last['vol_mean']
    return False, None, None

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg}
    requests.post(url, data=payload)

def main():
    coins = ["BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT","LINKUSDT","DOGEUSDT"]
    signals = []
    for coin in coins:
        signal, rsi, vol = check_signal(coin)
        if signal:
            signals.append(f"✅ ALIM SİNYALİ: {coin}\nRSI: {rsi:.1f}\nHacim x{vol:.2f}")
    if signals:
        send_telegram("\n\n".join(signals))
    else:
        send_telegram("⚪ Şu an güçlü sinyal bulunamadı.")

if __name__ == "__main__":
    main()
