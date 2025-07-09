import time
import requests
import pandas as pd
from bs4 import BeautifulSoup as bs
from datetime import datetime

# === CONFIG ===

BOT_TOKEN = '8127636976:AAEb4awyMSnNa2j-gSXCrmeDhDkNlf3IV-I'
CHAT_IDS = ['6680805526','-1002796457494']  # You can add multiple chat IDs here

#SLEEP_INTERVAL = 60  # 60 sec = 1 min
SLEEP_INTERVAL = 300  # 300 sec = 5 min
#SLEEP_INTERVAL = 900  # 900 sec = 15 min

SCANNERS = [
    {
        'SCREENER_NAME': 'Breakout After 20 Days Consolidation (Short Swing 1-7 Days)',
        'SCREENER_URL': 'https://chartink.com/screener/20-day-breakout-after-consolidation',
        'scan_clause': {
            'scan_clause': '( {57960} ( latest sma( latest volume , 20 ) > 500000 and latest close > 1 day ago max( 20 , latest high ) and 1 day ago  close <= 2 day ago  max( 20 , latest high ) and 1 day ago max( 5 , latest high ) < 5 days ago max( 15 , latest high ) and latest rsi( 14 ) > 60 and latest cci( 14 ) > 100 and latest adx( 14 ) > 20 and latest adx di positive( 14 ) >= latest adx di negative( 14 ) and latest close > latest vwap and latest volume > latest sma( latest volume , 20 ) * 1.5 and latest close * latest volume >= 40000000 ) )'
        }
    },
    {
        'SCREENER_NAME': 'Breakout after 4 Months (Strong Swing, Positional)',
        'SCREENER_URL': 'https://chartink.com/screener/4-month-fresh-breakout-scan-nifty-500',
        'scan_clause': {
            'scan_clause': '( {57960} ( latest close > 1 day ago close * 1.03 and 1 day ago close < 2 days ago max( 120 , latest high ) and latest close > 1 day ago max( 120 , latest high ) and 1 day ago  close <= 2 day ago  max( 120 , latest high ) and latest rsi( 14 ) > 60 and latest cci( 14 ) > 100 and latest adx( 14 ) > 20 and latest adx di positive( 14 ) >= latest adx di negative( 14 ) and latest close > latest vwap and latest volume > latest sma( latest volume , 120 ) * 1.5 and latest close * latest volume >= 40000000 and weekly close > weekly open ) )'
        }
    },
    {
        'SCREENER_NAME': 'Breakout with Strong Momentum & Volume (Futures - Short Swing)',
        'SCREENER_URL': 'https://chartink.com/screener/power-momentum-breakouts-futures',
        'scan_clause': {
            'scan_clause': '( {33489} ( ( {33489} ( ( {33489} ( latest volume > ( 2 * latest "sum( close  *  volume, 20 ) / sum( volume ,20 )" ) and latest close > ( 0.98 * latest high ) and latest close > 1 day ago close and latest rsi( 14 ) > 60 and latest cci( 14 ) > 110 and latest adx( 14 ) > 20 and latest volume >= 1000000 and latest adx di positive( 14 ) >= latest adx di negative( 14 ) and latest close > 1 day ago max( 20 , latest high ) and 1 day ago  close <= 2 day ago  max( 20 , latest high ) ) ) or( {33489} ( ( latest high - latest low ) > ( 1 day ago high - 1 day ago low ) and( latest high - latest low ) > ( 2 days ago high - 2 days ago low ) and( latest high - latest low ) > ( 3 days ago high - 3 days ago low ) and latest rsi( 14 ) > 60 and latest cci( 20 ) > 110 and latest adx( 14 ) > 20 and latest close > latest open and latest close > 1 day ago close and weekly close > weekly open and 1 day ago volume > 1000000 and 1 day ago ema( latest close , 20 ) > 1 day ago ema( 1 day ago close , 50 ) and latest vwap > 1 day ago vwap and latest vwap > 2 days ago vwap and latest vwap > 3 days ago vwap and [=1] 5 minute volume > 10000 and [=1] 10 minute high >= latest sma( latest close , 20 ) and [=2] 5 minute high >= latest sma( latest close , 20 ) and latest adx di positive( 14 ) > latest adx di negative( 14 ) and latest close > 1 day ago max( 20 , latest high ) and 1 day ago  close <= 2 day ago  max( 20 , latest high ) ) ) ) ) ) )'
        }
    }
    #You can add more scanners here
]

# === SEND TELEGRAM ALERT ===
def send_telegram_message(msg):
    try:
        for chat_id in CHAT_IDS:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            payload = {'chat_id': chat_id, 'text': msg}
            r = requests.post(url, data=payload)
            if not r.ok:
                print("❌ Telegram error:", r.text)
    except Exception as e:
        print("❌ Telegram exception:", e)


# === FETCH FROM CHARTINK ===
def chartink_scraper(url, scan_clause):
    try:
        with requests.Session() as s:
            r = s.get(url)
            soup = bs(r.text, "html.parser")
            csrf = soup.select_one("[name='csrf-token']")['content']
            s.headers['x-csrf-token'] = csrf
            s.headers['Content-Type'] = 'application/x-www-form-urlencoded'
            r = s.post('https://chartink.com/screener/process', data=scan_clause)
            df = pd.DataFrame().from_dict(r.json()['data'])
            return df
    except Exception as e:
        print("❌ Failed to fetch Chartink data:", e)
        return pd.DataFrame()


# === MAIN LOOP ===
if __name__ == "__main__":
    print("🚀 Chartink Scanner Started with regular refresh")

    seen_stocks = {scanner['SCREENER_NAME']: set() for scanner in SCANNERS}

    while True:
        now = datetime.now()
        current_time = now.strftime("%H:%M:%S")
        print(f"🕒 Checking at {current_time}")

        for scanner in SCANNERS:
            name = scanner['SCREENER_NAME']
            url = scanner['SCREENER_URL']
            clause = scanner['scan_clause']
            print(f"🔍 {name}")
            df = chartink_scraper(url, clause)


            if df.empty:
                print("ℹ️ No breakout stocks right now.\n")
            else:
                new_stocks = [row for _, row in df.iterrows() if row['nsecode'] not in seen_stocks[name]]
                if new_stocks:
                    lines = []
                    for row in new_stocks:
                        code = row['nsecode']
                        company_name = row['name']
                        price = row['close']
                        pct   = row['per_chg']
                        vol   = row['volume']
                        lines.append(f"💰 {code} ({company_name})\nCMP: ₹{price:.2f}   Vol: {vol:,}   Per.Chng: {pct:+.2f}% \n")
                        seen_stocks[name].add(code)

                    message = f"📈 Chartink Alert: {name}\n\n"+"\n"
                    message += "\n".join(lines)
                    send_telegram_message(message)

                    print(f"✅ Sent alert for: {', '.join([r['nsecode'] for r in new_stocks])}\n")
                else:
                    print("⚠️ No new stocks since last check.\n")

        time.sleep(SLEEP_INTERVAL)
