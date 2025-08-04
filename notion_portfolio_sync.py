"""notion_portfolio_sync.py ─ Update Notion DB with latest prices

HOW TO USE
1) pip install requests yfinance python-dotenv
2) .env 파일에↓ 두 줄 입력
   NOTION_TOKEN=secret_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   NOTION_DATABASE_ID=245c7ba9258080d7b6b0d6bc2f37de73
3) DB 페이지를 Portfolio Sync 통합(⚡)에 Invite
4) python notion_portfolio_sync.py   # 성공 후 크론·스케줄러 등록
"""

import os, time, requests, yfinance as yf
from datetime import datetime, timezone
from typing import Dict
from dotenv import load_dotenv

load_dotenv()
TOKEN  = os.getenv("NOTION_TOKEN")
DB_ID  = os.getenv("NOTION_DATABASE_ID")
HEAD   = {"Authorization": f"Bearer {TOKEN}",
          "Content-Type": "application/json",
          "Notion-Version": "2022-06-28"}

TICKERS = [
    "379800.KS","354500.KS","132030.KS","153130.KS",
    "VOO","BIL","BSCP",
    "BTC-USD","ETH-USD","GOLDKRX",
]

def page_id(ticker:str, _cache:Dict[str,str]={}) -> str:
    if ticker in _cache: return _cache[ticker]
    url=f"https://api.notion.com/v1/databases/{DB_ID}/query"
    payload={"filter":{"property":"Ticker","rich_text":{"equals":ticker}},"page_size":1}
    res=requests.post(url,headers=HEAD,json=payload,timeout=30).json()
    pid=res.get("results",[{}])[0].get("id")
    if not pid: raise ValueError(f"Ticker '{ticker}' not found")
    _cache[ticker]=pid; return pid

def set_price(pid:str, price:float):
    url=f"https://api.notion.com/v1/pages/{pid}"
    payload={"properties":{"Current Price":{"number":round(price,2)}}}
    requests.patch(url,headers=HEAD,json=payload,timeout=30)

def quote(t:str)->float:
    if t.endswith("-USD"):   # crypto
        s=t.split("-")[0].lower()
        return requests.get(f"https://api.coingecko.com/api/v3/simple/price?ids={s}&vs_currencies=usd",timeout=20).json().get(s,{}).get("usd",0)
    if t=="GOLDKRX":         # gold per gram
        oz=yf.Ticker("GC=F").history(period="1d")["Close"].iloc[-1]
        return oz/31.1035
    return yf.Ticker(t).history(period="1d")["Close"].iloc[-1]

def main():
    print("[Notion Sync]",datetime.now(timezone.utc).isoformat(timespec="seconds"))
    for tk in TICKERS:
        try:
            price=quote(tk); pid=page_id(tk); set_price(pid,price)
            print(f"✓ {tk}: {price}")
            time.sleep(0.3)
        except Exception as e:
            print(f"✗ {tk}: {e}")

if __name__=="__main__":
    main()
