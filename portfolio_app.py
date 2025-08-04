
# portfolio_app.py
"""Streamlit Personal Portfolio Dashboard
Run with:  streamlit run portfolio_app.py
Dependencies: pip install streamlit yfinance pandas requests plotly

Features
• Reads holdings from a CSV (portfolio.csv) or manual list fallback.
• Fetches latest prices for stocks/ETFs via yfinance and crypto via CoinGecko.
• Displays current value table + allocation pie chart.
• Auto‑refresh interval selectable in the sidebar.
"""

import time
import json
from pathlib import Path

import pandas as pd
import requests
import streamlit as st
import yfinance as yf
import plotly.express as px

# ----------------------------------------------------------------------
# 1. Holdings – either CSV or hard‑coded dictionary
# ----------------------------------------------------------------------
DEFAULT_HOLDINGS = [
    {"Account": "연금저축", "Ticker": "379800.KS", "Units": 20},
    {"Account": "ISA", "Ticker": "354500.KS", "Units": 30},
    {"Account": "ISA", "Ticker": "132030.KS", "Units": 25},
    {"Account": "ISA", "Ticker": "153130.KS", "Units": 80},
    {"Account": "해외", "Ticker": "VOO", "Units": 12},
    {"Account": "해외", "Ticker": "BIL", "Units": 30},
    {"Account": "해외", "Ticker": "BSCP", "Units": 40},
    {"Account": "해외", "Ticker": "BTC-USD", "Units": 0.15},
    {"Account": "해외", "Ticker": "ETH-USD", "Units": 1.2},
    {"Account": "금현물", "Ticker": "GOLDKRX", "Units": 10},  # 10g
]

csv_path = Path("portfolio.csv")
if csv_path.exists():
    holdings = pd.read_csv(csv_path)
else:
    holdings = pd.DataFrame(DEFAULT_HOLDINGS)

# ----------------------------------------------------------------------
# 2. UI
# ----------------------------------------------------------------------
st.set_page_config(page_title="My Portfolio Dashboard", layout="wide")
st.title("📊 Personal Portfolio Dashboard")

refresh_sec = st.sidebar.slider("Auto‑refresh (sec)", 30, 600, 120, 30)

# ----------------------------------------------------------------------
# 3. Fetch Prices
# ----------------------------------------------------------------------
@st.cache_data(ttl=refresh_sec)
def get_price(ticker: str) -> float:
    if ticker.endswith("-USD"):
        # Crypto via CoinGecko
        symbol = ticker.split("-")[0].lower()
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={symbol}&vs_currencies=usd"
        r = requests.get(url, timeout=20).json()
        return r.get(symbol, {}).get("usd", 0)
    elif ticker == "GOLDKRX":
        # Gold price per gram in USD using LBMA + USDKRW
        gold_oz = yf.Ticker("GC=F").history(period="1d")["Close"].iloc[-1]
        price_per_g = gold_oz / 31.1035
        return price_per_g
    else:
        price = yf.Ticker(ticker).history(period="1d")["Close"].iloc[-1]
        return price

prices = []
for tkr in holdings["Ticker"]:
    try:
        prices.append(get_price(tkr))
    except Exception:
        prices.append(0)

holdings["Price"] = prices
holdings["Value"] = holdings["Units"] * holdings["Price"]
total_value = holdings["Value"].sum()

# ----------------------------------------------------------------------
# 4. Display
# ----------------------------------------------------------------------
st.metric("Total Market Value (USD)", f"${total_value:,.2f}")

st.dataframe(
    holdings[["Account", "Ticker", "Units", "Price", "Value"]]
    .sort_values("Value", ascending=False)
    .style.format({"Units": "{:.3f}", "Price": "${:,.2f}", "Value": "${:,.2f}"}),
    use_container_width=True,
)

fig = px.pie(
    holdings,
    names="Ticker",
    values="Value",
    title="Allocation by Ticker",
    hole=0.4,
)
st.plotly_chart(fig, use_container_width=True)

st.caption("Last updated: " + time.strftime("%Y-%m-%d %H:%M:%S"))

# ▼ 파일 맨 아래
try:
    import notion_portfolio_sync as nps
    nps.main()          # 노션 가격 동기화 1회 실행
except Exception as e:
    st.warning(f"Notion sync failed: {e}")
