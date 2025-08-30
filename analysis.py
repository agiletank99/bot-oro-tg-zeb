import os
import yfinance as yf
import pandas as pd

def calculate_ema(data, length):
    return data['Close'].ewm(span=length, adjust=False).mean()

def calculate_rsi(data, length=14):
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=length).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=length).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_atr(data, length=14):
    tr1 = data['High'] - data['Low']
    tr2 = abs(data['High'] - data['Close'].shift(1))
    tr3 = abs(data['Low'] - data['Close'].shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.ewm(span=length, adjust=False).mean()

def calculate_macd(data, fast=12, slow=26, signal=9):
    ema_fast = data['Close'].ewm(span=fast, adjust=False).mean()
    ema_slow = data['Close'].ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line, signal_line

def get_market_data(ticker="GC=F"):
    try:
        data_d1 = yf.download(ticker, period="1y", interval="1d", progress=False, auto_adjust=False)
        data_h4 = yf.download(ticker, period="60d", interval="1h", progress=False, auto_adjust=False)
        data = {'D1': data_d1, 'H4': data_h4.resample('4h').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'}).dropna()}
        for df in data.values():
            df['EMA_50'] = calculate_ema(df, 50); df['EMA_200'] = calculate_ema(df, 200)
            df['RSI_14'] = calculate_rsi(df, 14); df['ATR_14'] = calculate_atr(df, 14)
            df['MACD_line'], df['MACD_signal'] = calculate_macd(df)
        return data
    except Exception as e:
        print(f"Errore recupero dati: {e}"); return None

def analyze_market():
    data = get_market_data()
    if data is None or data['D1'].empty: return "ERRORE", "Dati non disponibili.", "N/A", None, None, None
    d1, h4 = data['D1'].iloc[-2], data['H4'].iloc[-2]
    score, mot_tecniche = 0, []
    if d1['Close'] > d1['EMA_50']: score += 1; mot_tecniche.append("Trend D1 LONG.")
    else: score -= 1; mot_tecniche.append("Trend D1 SHORT.")
    if d1['RSI_14'] < 30: score += 1; mot_tecniche.append("RSI D1 Ipervenduto.")
    if d1['RSI_14'] > 70: score -= 1; mot_tecniche.append("RSI D1 Ipercomprato.")
    if h4['MACD_line'] > h4['MACD_signal']: score += 1; mot_tecniche.append("MACD H4 LONG.")
    else: score -= 1; mot_tecniche.append("MACD H4 SHORT.")
    decisione = "MANTIENI"
    if score >= 2: decisione = "APRI LONG"
    elif score <= -2: decisione = "APRI SHORT"
    price, atr = data['D1'].iloc[-1]['Close'], data['D1'].iloc[-1]['ATR_14']
    return decisione, " ".join(mot_tecniche), "N/A", price, atr, data