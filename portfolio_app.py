"""Streamlit Personal Portfolio Dashboard
$ streamlit run portfolio_app.py
Dependencies: streamlit yfinance pandas requests plotly
"""

import time
from pathlib import Path
from typing import Dict

import pandas as pd
import requests
import streamlit as st
import yfinance as yf
import plotly.express as px

# ─── 1. 기본 보유 목록 ─────────────────────────────────────────
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
    {"Account": "금현물", "Ticker": "GOLDKRX", "Units": 10},  # g 단위
]

csv_path = Path("portfolio.csv")
holdings = pd.read_csv(csv_path) if csv_path.exists() else pd.DataFrame(DEFAULT_HOLDINGS)

# ─── 2. Streamlit UI ──────────────────────────────────────────
st.set_page_config(page_title="My Portfolio Dashboard", layout="wide")
st.title("📊 Personal Portfolio Dashboard")
refresh_sec = st.sidebar.slider("Auto-refresh (sec)", 30, 600, 120, 30)

# ─── 3. 시세 수집 함수 ───────────────────────────────────────
COINGECKO_MAP: Dict[str, str] = {"btc-usd": "bitcoin", "eth-usd": "ethereum"}

@st.cache_data(ttl=refresh_sec)
def get_price(ticker: str) -> float:
    """yfinance / CoinGecko / Gold per g"""
    if ticker.endswith("-USD"):
        cg_id = COINGECKO_MAP.get(ticker.lower(), ticker.split("-")[0].lower())
        r = requests.get(
            f"https://api.coingecko.com/api/v3/simple/price"
            f"?ids={cg_id}&vs_currencies=usd",
            timeout=20,
        ).json()
        return r.get(cg_id, {}).get("usd", 0.0)

    if ticker == "GOLDKRX":
        oz = yf.Ticker("GC=F").history(period="1d")["Close"].iloc[-1]
        return oz / 31.1035

    data = yf.Ticker(ticker).history(period="1d")
    return float(data["Close"].iloc[-1]) if not data.empty else 0.0


holdings["Price"] = [get_price(t) for t in holdings["Ticker"]]
holdings["Value"] = holdings["Units"] * holdings["Price"]
total_value = holdings["Value"].sum()

# ─── 4. 대시보드 표시 ────────────────────────────────────────
st.metric("Total Market Value (USD)", f"${total_value:,.2f}")

st.dataframe(
    holdings[["Account", "Ticker", "Units", "Price", "Value"]]
    .sort_values("Value", ascending=False)
    .style.format({"Units": "{:.3f}", "Price": "${:,.2f}", "Value": "${:,.2f}"}),
    use_container_width=True,
)

fig = px.pie(
    holdings, names="Ticker", values="Value",
    title="Allocation by Ticker", hole=0.4,
)
st.plotly_chart(fig, use_container_width=True)

st.caption("Last updated: " + time.strftime("%Y-%m-%d %H:%M:%S"))

# ─── 5. Notion 가격 동기화 1회 트리거 ───────────────────────
try:
    from notion_portfolio_sync import main as sync_notion
    sync_notion()
except Exception as e:
    st.warning(f"Notion sync failed: {e}")
