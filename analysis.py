# analysis.py (Versione FMP - Stabile e Robusta)
import os
import requests
import pandas as pd
from newsapi import NewsApiClient

# --- CHIAVI API ---
FMP_API_KEY = os.environ.get("FMP_API_KEY")
NEWS_API_KEY = os.environ.get("NEWS_API_KEY")

# --- Funzioni Indicatori (usano nomi di colonna minuscoli internamente) ---
def calculate_ema(data, length): return data['close'].ewm(span=length, adjust=False).mean()
def calculate_rsi(data, length=14):
    delta = data['close'].diff(); gain = (delta.where(delta > 0, 0)).rolling(window=length).mean(); loss = (-delta.where(delta < 0, 0)).rolling(window=length).mean()
    rs = gain / loss; return 100 - (100 / (1 + rs))
def calculate_atr(data, length=14):
    tr1 = data['high'] - data['low']; tr2 = abs(data['high'] - data['close'].shift(1)); tr3 = abs(data['low'] - data['close'].shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1); return tr.ewm(span=length, adjust=False).mean()
def calculate_macd(data, fast=12, slow=26, signal=9):
    ema_fast = data['close'].ewm(span=fast, adjust=False).mean(); ema_slow = data['close'].ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow; return macd_line, macd_line.ewm(span=signal, adjust=False).mean()
def calculate_bollinger_bands(data, window=20, std_dev=2):
    middle_band = data['close'].rolling(window=window).mean(); std = data['close'].rolling(window=window).std()
    return middle_band + (std * std_dev), middle_band - (std * std_dev)

# --- NUOVA FUNZIONE DATI CON FMP E VALIDAZIONE ---
def get_market_data(symbol="XAUUSD"):
    if not FMP_API_KEY:
        return ("ERRORE", "Chiave API FMP non configurata.")
    try:
        url_h = f"https://financialmodelingprep.com/api/v3/historical-chart/1hour/{symbol}?apikey={FMP_API_KEY}"
        url_d = f"https://financialmodelingprep.com/api/v3/historical-price-full/{symbol}?apikey={FMP_API_KEY}"

        response_h = requests.get(url_h)
        response_d = requests.get(url_d)
        
        response_h.raise_for_status()
        response_d.raise_for_status()

        json_h = response_h.json()
        json_d = response_d.json()

        if not isinstance(json_h, list) or not json_h:
            error_message = json_h.get('Error Message', 'Risposta dati orari non valida da FMP.')
            return ("ERRORE", error_message)
        
        if 'historical' not in json_d or not isinstance(json_d['historical'], list) or not json_d['historical']:
            error_message = json_d.get('Error Message', 'Risposta dati giornalieri non valida da FMP.')
            return ("ERRORE", error_message)

        data_h = pd.DataFrame(json_h)
        data_d = pd.DataFrame(json_d['historical'])
        
        if data_h.empty or data_d.empty:
            return ("ERRORE", "FMP ha restituito dati vuoti.")

        for df in [data_h, data_d]:
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            df.sort_index(inplace=True)

        data = {'D1': data_d, 'H4': data_h.resample('4h').agg({'open':'first', 'high':'max', 'low':'min', 'close':'last', 'volume':'sum'}).dropna()}
        
        for df in data.values():
            # Calcoliamo prima con i nomi minuscoli di FMP
            df['EMA_50']=calculate_ema(df,50); df['EMA_200']=calculate_ema(df,200)
            df['RSI_14']=calculate_rsi(df,14);
            df['MACD_line'], df['MACD_signal']=calculate_macd(df)
            df['BBU'], df['BBL']=calculate_bollinger_bands(df)
            # Ora rinominiamo le colonne per coerenza con il resto del codice
            df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'}, inplace=True)
            # Calcoliamo l'ATR per ultimo perché richiede i nomi di colonna maiuscoli
            df['ATR_14']=calculate_atr(df,14)

        return ("SUCCESSO", data)
    except requests.exceptions.HTTPError as http_err:
         return ("ERRORE", f"Errore HTTP da FMP: {http_err.response.status_code} - {http_err.response.text}")
    except Exception as e:
        return ("ERRORE", f"Errore imprevisto durante l'analisi FMP: {e}")

# --- Le altre funzioni rimangono identiche ---
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
        if sentiment_score >= 2: return "BULLISH";
        if sentiment_score <= -2: return "BEARISH"
        return "NEUTRAL"
    except Exception as e:
        print(f"Errore News API: {e}"); return "NEUTRAL (Errore API)"

def analyze_from_data(data):
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

def analyze_market():
    status, data_or_error = get_market_data()
    if status == "ERRORE":
        return "ERRORE", data_or_error, "N/A", None, None, None
    return analyze_from_data(data_or_error)```

### **Azione Finale**

1.  **Sostituisci** il codice in `analysis.py` su GitHub.
2.  **Fai il commit.**
3.  **Fai il redeploy** su Koyeb.

Ora il bot sarà molto più specifico nel dirti perché FMP sta fallendo, se sta fallendo. Questo ci darà l'indizio finale.
