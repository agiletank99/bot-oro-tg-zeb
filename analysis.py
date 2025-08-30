# analysis.py (Versione Alpha Vantage)
import os
import pandas as pd
from alpha_vantage.timeseries import TimeSeries
from newsapi import NewsApiClient

# --- NUOVE CHIAVI API ---
ALPHA_VANTAGE_API_KEY = os.environ.get("ALPHA_VANTAGE_API_KEY")
NEWS_API_KEY = os.environ.get("NEWS_API_KEY")

# --- Funzioni Indicatori (invariate) ---
def calculate_ema(data, length): return data['Close'].ewm(span=length, adjust=False).mean()
def calculate_rsi(data, length=14):
    delta = data['Close'].diff(); gain = (delta.where(delta > 0, 0)).rolling(window=length).mean(); loss = (-delta.where(delta < 0, 0)).rolling(window=length).mean()
    rs = gain / loss; return 100 - (100 / (1 + rs))
def calculate_atr(data, length=14):
    tr1=data['High']-data['Low']; tr2=abs(data['High']-data['Close'].shift(1)); tr3=abs(data['Low']-data['Close'].shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1); return tr.ewm(span=length, adjust=False).mean()
def calculate_macd(data, fast=12, slow=26, signal=9):
    ema_fast = data['Close'].ewm(span=fast, adjust=False).mean(); ema_slow = data['Close'].ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow; return macd_line, macd_line.ewm(span=signal, adjust=False).mean()
def calculate_bollinger_bands(data, window=20, std_dev=2):
    middle_band = data['Close'].rolling(window=window).mean(); std = data['Close'].rolling(window=window).std()
    return middle_band + (std * std_dev), middle_band - (std * std_dev)

# --- NUOVA FUNZIONE DATI CON ALPHA VANTAGE ---
def get_market_data(symbol="XAUUSD"):
    if not ALPHA_VANTAGE_API_KEY: return None
    try:
        ts = TimeSeries(key=ALPHA_VANTAGE_API_KEY, output_format='pandas')
        # Per l'oro fisico, il simbolo è XAUUSD. Alpha Vantage non usa ticker come GC=F
        # Scarichiamo dati orari (per H4) e giornalieri (per D1)
        data_h, _ = ts.get_intraday(symbol=symbol, interval='60min', outputsize='full')
        data_d, _ = ts.get_daily(symbol=symbol, outputsize='full')

        # Rinominiamo le colonne per uniformità
        data_h.rename(columns={'1. open': 'Open', '2. high': 'High', '3. low': 'Low', '4. close': 'Close', '5. volume': 'Volume'}, inplace=True)
        data_d.rename(columns={'1. open': 'Open', '2. high': 'High', '3. low': 'Low', '4. close': 'Close', '5. volume': 'Volume'}, inplace=True)

        # Convertiamo i dati in numerico
        for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
            data_h[col] = pd.to_numeric(data_h[col]); data_d[col] = pd.to_numeric(data_d[col])

        # Invertiamo l'ordine (Alpha Vantage li dà dal più recente al più vecchio)
        data_h = data_h.iloc[::-1]; data_d = data_d.iloc[::-1]

        data = {'D1': data_d, 'H4': data_h.resample('4h').agg({'Open':'first', 'High':'max', 'Low':'min', 'Close':'last', 'Volume':'sum'}).dropna()}
        
        for df in data.values():
            df['EMA_50']=calculate_ema(df,50); df['EMA_200']=calculate_ema(df,200)
            df['RSI_14']=calculate_rsi(df,14); df['ATR_14']=calculate_atr(df,14)
            df['MACD_line'], df['MACD_signal']=calculate_macd(df)
            df['BBU'], df['BBL']=calculate_bollinger_bands(df)
        return data
    except Exception as e:
        print(f"Errore Alpha Vantage: {e}"); return None

# --- Le altre funzioni (get_news_sentiment, analyze_market) rimangono identiche ---
def get_news_sentiment():
    if not NEWS_API_KEY: return "NEUTRAL (API Key non configurata)"
    try:
        newsapi = NewsApiClient(api_key=NEWS_API_KEY)
        query = 'gold price OR XAUUSD OR federal reserve interest rates OR inflation'
        articles = newsapi.get_everything(q=query, language='en', sort_by='publishedAt', page_size=20)
        sentiment_score = 0; keywords_bullish = ['rally','rises','safe-haven','surges','demand','cut rates']; keywords_bearish = ['falls','drops','pressure','strong dollar','hike rates']
        for article in articles['articles']:
            title = article.get('title', '').lower()
            if any(keyword in title for keyword in keywords_bullish): sentiment_score += 1
            if any(keyword in title for keyword in keywords_bearish): sentiment_score -= 1
        if sentiment_score >= 2: return "BULLISH"
        if sentiment_score <= -2: return "BEARISH"
        return "NEUTRAL"
    except Exception as e:
        print(f"Errore News API: {e}"); return "NEUTRAL (Errore API)"

def analyze_market():
    data = get_market_data()
    if data is None or data['D1'].empty: return "ERRORE", "Dati non disponibili.", "N/A", None, None, None
    d1, h4 = data['D1'].iloc[-2], data['H4'].iloc[-2]; current_price_info = data['D1'].iloc[-1]
    score, mot_tecniche = 0, []
    if d1['Close'] > d1['EMA_50']: score += 1; mot_tecniche.append("Trend D1 LONG.")
    else: score -= 1; mot_tecniche.append("Trend D1 SHORT.")
    if h4['MACD_line'] > h4['MACD_signal']: score += 1; mot_tecniche.append("MACD H4 LONG.")
    else: score -= 1; mot_tecniche.append("MACD H4 SHORT.")
    if current_price_info['Close'] < h4['BBL']: score += 1; mot_tecniche.append("Prezzo sotto Bollinger Band.")
    if current_price_info['Close'] > h4['BBU']: score -= 1; mot_tecniche.append("Prezzo sopra Bollinger Band.")
    sentiment = get_news_sentiment(); motivazione_fondamentale = f"Sentiment: {sentiment}."
    if sentiment == "BULLISH": score += 1
    elif sentiment == "BEARISH": score -= 1
    decisione = "MANTIENI"
    if score >= 2: decisione = "APRI LONG"
    elif score <= -2: decisione = "APRI SHORT"
    return decisione, " ".join(mot_tecniche), motivazione_fondamentale, current_price_info['Close'], current_price_info['ATR_14'], data
