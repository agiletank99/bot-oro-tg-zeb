# analysis.py (Fase 2: Sentiment e Volatilità)
import os
import yfinance as yf
import pandas as pd
from newsapi import NewsApiClient

NEWS_API_KEY = os.environ.get("NEWS_API_KEY")

# --- Funzioni Indicatori ---
def calculate_ema(data, length): return data['Close'].ewm(span=length, adjust=False).mean()
def calculate_rsi(data, length=14):
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=length).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=length).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))
def calculate_atr(data, length=14):
    tr1 = data['High'] - data['Low']; tr2 = abs(data['High'] - data['Close'].shift(1)); tr3 = abs(data['Low'] - data['Close'].shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.ewm(span=length, adjust=False).mean()
def calculate_macd(data, fast=12, slow=26, signal=9):
    ema_fast = data['Close'].ewm(span=fast, adjust=False).mean(); ema_slow = data['Close'].ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    return macd_line, macd_line.ewm(span=signal, adjust=False).mean()

# --- NUOVO INDICATORE: BANDE DI BOLLINGER ---
def calculate_bollinger_bands(data, window=20, std_dev=2):
    middle_band = data['Close'].rolling(window=window).mean()
    std = data['Close'].rolling(window=window).std()
    upper_band = middle_band + (std * std_dev)
    lower_band = middle_band - (std * std_dev)
    return upper_band, lower_band

# --- NUOVA FUNZIONE: ANALISI SENTIMENT ---
def get_news_sentiment():
    if not NEWS_API_KEY:
        return "NEUTRAL (API Key non configurata)"
    try:
        newsapi = NewsApiClient(api_key=NEWS_API_KEY)
        query = 'gold price OR XAUUSD OR federal reserve interest rates OR inflation'
        articles = newsapi.get_everything(q=query, language='en', sort_by='publishedAt', page_size=20)
        
        sentiment_score = 0
        keywords_bullish = ['rally', 'rises', 'safe-haven', 'surges', 'demand', 'cut rates']
        keywords_bearish = ['falls', 'drops', 'pressure', 'strong dollar', 'hike rates']
        
        for article in articles['articles']:
            title = article.get('title', '').lower()
            if any(keyword in title for keyword in keywords_bullish): sentiment_score += 1
            if any(keyword in title for keyword in keywords_bearish): sentiment_score -= 1
        
        if sentiment_score >= 2: return "BULLISH"
        if sentiment_score <= -2: return "BEARISH"
        return "NEUTRAL"
    except Exception as e:
        print(f"Errore News API: {e}")
        return "NEUTRAL (Errore API)"

def get_market_data(ticker="GC=F"):
    try:
        data_d1 = yf.download(ticker, period="1y", interval="1d", progress=False, auto_adjust=False)
        data_h4 = yf.download(ticker, period="60d", interval="1h", progress=False, auto_adjust=False)
        data = {'D1': data_d1, 'H4': data_h4.resample('4h').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'}).dropna()}
        
        for df in data.values():
            df['EMA_50'] = calculate_ema(df, 50); df['EMA_200'] = calculate_ema(df, 200)
            df['RSI_14'] = calculate_rsi(df, 14); df['ATR_14'] = calculate_atr(df, 14)
            df['MACD_line'], df['MACD_signal'] = calculate_macd(df)
            df['BBU'], df['BBL'] = calculate_bollinger_bands(df) # Aggiunta Bande di Bollinger
        return data
    except Exception as e:
        print(f"Errore recupero dati: {e}"); return None

def analyze_market():
    data = get_market_data()
    if data is None or data['D1'].empty: return "ERRORE", "Dati non disponibili.", "N/A", None, None, None
    
    d1, h4 = data['D1'].iloc[-2], data['H4'].iloc[-2]
    current_price_info = data['D1'].iloc[-1]
    score, mot_tecniche = 0, []
    
    # 1. Analisi Trend
    if d1['Close'] > d1['EMA_50']: score += 1; mot_tecniche.append("Trend D1 LONG.")
    else: score -= 1; mot_tecniche.append("Trend D1 SHORT.")
    
    # 2. Analisi Momentum
    if h4['MACD_line'] > h4['MACD_signal']: score += 1; mot_tecniche.append("MACD H4 LONG.")
    else: score -= 1; mot_tecniche.append("MACD H4 SHORT.")
    
    # 3. Analisi Ipercomprato/Ipervenduto (Mean Reversion)
    if current_price_info['Close'] < h4['BBL']: score += 1; mot_tecniche.append("Prezzo sotto Bollinger Band (segnale LONG).")
    if current_price_info['Close'] > h4['BBU']: score -= 1; mot_tecniche.append("Prezzo sopra Bollinger Band (segnale SHORT).")

    # --- INTEGRAZIONE SENTIMENT ---
    sentiment = get_news_sentiment()
    motivazione_fondamentale = f"Sentiment notizie: {sentiment}."
    if sentiment == "BULLISH": score += 1
    elif sentiment == "BEARISH": score -= 1

    decisione = "MANTIENI"
    if score >= 2: decisione = "APRI LONG"
    elif score <= -2: decisione = "APRI SHORT"
    
    return decisione, " ".join(mot_tecniche), motivazione_fondamentale, current_price_info['Close'], current_price_info['ATR_14'], data
