"""notion_portfolio_sync.py ─ Notion DB에 실시간 시세 입력

HOW TO USE
1) pip install requests yfinance python-dotenv
2) .env 파일
   NOTION_TOKEN=secret_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   NOTION_DATABASE_ID=245c7ba925808009bebcf1228999cfbc
3) 표(DB) 페이지를 통합(⚡)에 Invite → Full access
4) python notion_portfolio_sync.py
   (자동화: GitHub Actions · Streamlit Cloud 스케줄러)
"""

import os, time, requests, yfinance as yf
from datetime import datetime, timezone
from typing import Dict
from dotenv import load_dotenv

load_dotenv()
TOKEN  = os.getenv("NOTION_TOKEN")
DB_ID  = os.getenv("NOTION_DATABASE_ID")
HEAD   = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

# ──────────────────────────────────────────────────────────────
TICKERS = [
    "379800.KS", "354500.KS", "132030.KS", "153130.KS",
    "VOO", "BIL", "BSCP",
    "BTC-USD", "ETH-USD", "GOLDKRX",
]

COINGECKO_MAP = {              # 티커 → CoinGecko id
    "btc-usd": "bitcoin",
    "eth-usd": "ethereum",
}

# ──────────────────────────────────────────────────────────────
def ensure_page(ticker: str, _cache: Dict[str, str] = {}) -> str:
    """Ticker 행 ID 반환. 없으면 새로 생성."""
    if ticker in _cache:
        return _cache[ticker]

    q_url = f"https://api.notion.com/v1/databases/{DB_ID}/query"
    query = {"filter": {"property": "Ticker",
                        "rich_text": {"equals": ticker}},
             "page_size": 1}
    r = requests.post(q_url, headers=HEAD, json=query, timeout=30).json()
    pid = r.get("results", [{}])[0].get("id")
    if pid:                       # 이미 존재
        _cache[ticker] = pid
        return pid

    # 신규 페이지(행) 생성
    r = requests.post(
        "https://api.notion.com/v1/pages",
        headers=HEAD,
        json={
            "parent": {"database_id": DB_ID},
            "properties": {
                "Ticker":   {"rich_text": [{"text": {"content": ticker}}]},
                "Account":  {"select":    {"name": "미분류"}},
                "Units":    {"number": 0},
            },
        },
        timeout=30,
    )
    r.raise_for_status()
    pid = r.json()["id"]
    _cache[ticker] = pid
    return pid


def set_price(page_id: str, price: float) -> None:
    """Current Price 숫자 속성 업데이트"""
    url = f"https://api.notion.com/v1/pages/{page_id}"
    payload = {"properties": {"Current Price": {"number": round(price, 2)}}}
    requests.patch(url, headers=HEAD, json=payload, timeout=30).raise_for_status()

def set_value(page_id: str, units: float, price: float):
    url = f"https://api.notion.com/v1/pages/{page_id}"
    payload = {"properties": {"Market Value": {"number": round(units * price, 2)}}}
    requests.patch(url, headers=HEAD, json=payload, timeout=30)


def quote(ticker: str) -> float:
    """USD 가격 반환 (주식/ETF, Crypto, Gold)"""
    if ticker.endswith("-USD"):                        # Crypto
        cg_id = COINGECKO_MAP.get(ticker.lower(), ticker.split("-")[0].lower())
        r = requests.get(
            f"https://api.coingecko.com/api/v3/simple/price"
            f"?ids={cg_id}&vs_currencies=usd", timeout=20
        ).json()
        return r.get(cg_id, {}).get("usd", 0.0)

    if ticker == "GOLDKRX":                            # 금(g) USD
        oz = yf.Ticker("GC=F").history(period="1d")["Close"].iloc[-1]
        return oz / 31.1035

    # 주식/ETF
    data = yf.Ticker(ticker).history(period="1d")
    return float(data["Close"].iloc[-1]) if not data.empty else 0.0


def main() -> None:
    print("[Notion Sync]", datetime.now(timezone.utc).isoformat(timespec="seconds"))
    for tk in TICKERS:
        try:
            price = quote(tk)
            pid   = ensure_page(tk)
            set_price(pid, price)
            print(f"✓ {tk}: {price}")
            time.sleep(0.3)  # rate-limit 예방
        except Exception as e:
            print(f"✗ {tk}: {e}")


if __name__ == "__main__":
    main()
