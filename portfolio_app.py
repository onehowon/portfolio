import os, time, json, requests, dotenv
from pathlib import Path

import pandas as pd
import streamlit as st
import yfinance as yf
import plotly.express as px
dotenv.load_dotenv()                       # .env 로부터 토큰/ID 읽기

print("DBG-ENV", os.getenv("NOTION_TOKEN")[:10], os.getenv("NOTION_DATABASE_ID"))


NOTION_TOKEN  = os.getenv("NOTION_TOKEN")
NOTION_DB_ID  = os.getenv("NOTION_DATABASE_ID")
HEAD = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

def load_holdings_from_notion() -> pd.DataFrame:
    """Notion 포트폴리오 DB → pandas.DataFrame"""
    rows, next_cursor = [], None
    while True:
        body = {"page_size": 100}
        if next_cursor:
            body["start_cursor"] = next_cursor
        r = requests.post(
            f"https://api.notion.com/v1/databases/{NOTION_DB_ID}/query",
            headers=HEAD, json=body, timeout=30).json()
        rows.extend(r["results"])
        next_cursor = r.get("next_cursor")
        if not r.get("has_more"): break

    def _prop(p, key):
        return p.get(key, {}).get("rich_text", [{}])[0].get("plain_text", "")

    def _num(p, key):
        return p.get(key, {}).get("number", 0)

    data = []
    for row in rows:
        prop = row["properties"]
        data.append({
            "Account":  prop["Account"]["select"]["name"],
            "Ticker":   _prop(prop, "Ticker"),
            "Units":    _num(prop, "Units"),
        })
    return pd.DataFrame(data)

DEFAULT_HOLDINGS = []

holdings = load_holdings_from_notion()        # ← 교체
