import requests
import pandas as pd
import numpy as np
import random
import time
from sklearn.linear_model import LinearRegression


def fetch_data(pair_code="CRYIDX.B", timeframe="60", load_count=0, max_retries=5, retry_delay=3):
    retries = 0
    while retries < max_retries:
        try:

            timeframe = 30 if timeframe == '30s' else int(timeframe) * 60
            random_uid = random.randint(10**20, 10**21 - 1)
            url = f"https://tradingpoin.com/chart/api/data?type=json&token=&pair_code=CRYIDX.B&timeframe={timeframe}&load_count={load_count}&source=Binomo&val=Z-CRY/IDX&indicator[the_signal]=null&indicator[the_signal_param1]=null&indicator[the_signal_param2]=null&indicator[the_signal_param3]=null&uid={random_uid}"
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data_json = response.json()

            if "data" not in data_json or not data_json["data"]:
                print(f"[Warning] Data kosong, mencoba lagi (retry {retries+1})...")
                retries += 1
                time.sleep(retry_delay)
                continue

            return data_json["data"]
        
        except (requests.exceptions.RequestException, ValueError) as e:
            print(f"[Error] Gagal ambil data: {e}. Mencoba lagi (retry {retries+1})...")
            retries += 1
            time.sleep(retry_delay)

    print("[Fatal] Gagal mengambil data setelah beberapa percobaan.")
    return None

def add_technical_indicators(df):
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
    df['close'] = pd.to_numeric(df['close'], errors='coerce')
    
    # SMA dan EMA 20
    df['SMA20'] = df['close'].rolling(window=20).mean()
    df['EMA20'] = df['close'].ewm(span=20, adjust=False).mean()

    # MACD
    ema12 = df['close'].ewm(span=12, adjust=False).mean()
    ema26 = df['close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = ema12 - ema26
    df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()

    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))

    return df

def linear_regression(df, max_dev_multiplier=3):
    # Konversi datetime ke detik UNIX dan ke array NumPy
    waktu_numeric = np.array(df['datetime'].astype(np.int64) // 10**9).reshape(-1, 1)
    harga = df['close'].values

    # Model regresi linier
    model = LinearRegression()
    model.fit(waktu_numeric, harga)
    prediksi = model.predict(waktu_numeric)
    slope = model.coef_[0]

    residual = harga - prediksi
    std_dev = np.std(residual)
    max_residual = np.max(np.abs(residual))
    optimal_levels = int(np.ceil(max_residual / std_dev))
    levels = min(optimal_levels, max_dev_multiplier * 3)

    toleransi_levels = [std_dev * (i + 1) for i in range(levels)]
    toleransi_atas = [prediksi + tol for tol in toleransi_levels]
    toleransi_bawah = [prediksi - tol for tol in toleransi_levels]

    return {
        'prediksi': prediksi,
        'std_dev': std_dev,
        'levels': levels,
        'toleransi_atas': toleransi_atas,
        'toleransi_bawah': toleransi_bawah,
        'slope': slope
    }


def kirim_telegram(message, bot_token, chat_id):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'HTML'
    }
    try:
        response = requests.post(url, data=payload)
        return response.json()
    except Exception as e:
        print(f"Error kirim Telegram: {e}")
        return None    
