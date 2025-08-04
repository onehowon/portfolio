# portfolio_app.py
import os, time, json, requests, dotenv
from pathlib import Path
import pandas as pd
import streamlit as st
import yfinance as yf
import plotly.express as px

# ─── 1. ENV & Notion API ────────────────────────────────────
dotenv.load_dotenv()                       # .env (로컬) 로드

NOTION_TOKEN = os.getenv("NOTION_TOKEN", "")
NOTION_DB_ID = os.getenv("NOTION_DATABASE_ID", "")
print("DBG-ENV", NOTION_TOKEN[:10], NOTION_DB_ID[:8])

HEAD = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

def load_holdings_from_notion() -> pd.DataFrame:
    rows, cursor = [], None
    while True:
        body = {"page_size": 100, **({"start_cursor": cursor} if cursor else {})}
        r = requests.post(
            f"https://api.notion.com/v1/databases/{NOTION_DB_ID}/query",
            headers=HEAD, json=body, timeout=30
        ).json()
        rows.extend(r["results"])
        cursor = r.get("next_cursor")
        if not r.get("has_more"):
            break

    def _prop(p, k):
        return p.get(k, {}).get("rich_text", [{}])[0].get("plain_text", "")

    def _num(p, k):
        return p.get(k, {}).get("number", 0.0)

    data = []
    for row in rows:
        prop = row["properties"]
        data.append(
            {
                "Account": prop["Account"]["select"]["name"],
                "Ticker": _prop(prop, "Ticker"),
                "Units": _num(prop, "Units"),
            }
        )
    return pd.DataFrame(data)

# ─── 2. 가격 수집 함수 ──────────────────────────────────────
COINGECKO_MAP = {"btc-usd": "bitcoin", "eth-usd": "ethereum"}

@st.cache_data(ttl=120)        # 기본 2분마다 새로 고침
def get_price(ticker: str) -> float:
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


# ─── 3. Streamlit UI ────────────────────────────────────────
st.set_page_config(page_title="My Portfolio Dashboard", layout="wide")
st.title("📊 Personal Portfolio Dashboard")

refresh_sec = st.sidebar.slider("Auto-refresh (sec)", 30, 600, 120, 30)
st.cache_data.clear()                       # 슬라이더 조정 시 캐시 초기화

holdings = load_holdings_from_notion()
if holdings.empty:
    st.warning("⚠️ Notion DB에서 데이터를 읽지 못했습니다.")
    st.stop()

holdings["Price"] = [get_price(t) for t in holdings["Ticker"]]
holdings["Value"] = holdings["Units"] * holdings["Price"]
total_value = holdings["Value"].sum()

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

# ─── 4. 즉시 수동 새로 고침 버튼 ────────────────────────────
if st.sidebar.button("🔄 Refresh now"):
    st.cache_data.clear()
    st.rerun()
