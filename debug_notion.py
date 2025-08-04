# debug_notion.py ─ 진짜 연결 상태 점검
import os, requests, dotenv, json, textwrap
dotenv.load_dotenv()

token  = os.getenv("NOTION_TOKEN")
db_id  = os.getenv("NOTION_DATABASE_ID")
print("TOKEN  :", token[:10], "...")          # 로드 여부 확인
print("DB-ID :", db_id)

HEAD = {
    "Authorization": f"Bearer {token}",
    "Notion-Version": "2022-06-28",
}

# 1️⃣ 메타데이터 요청
meta_r = requests.get(f"https://api.notion.com/v1/databases/{db_id}", headers=HEAD)
print("GET /databases status →", meta_r.status_code)
print(textwrap.shorten(meta_r.text, 300))

# 2️⃣ 행 3개 미리보기
q_r = requests.post(f"https://api.notion.com/v1/databases/{db_id}/query",
                    headers=HEAD, json={"page_size": 3})
print("QUERY status →", q_r.status_code, "rows =", len(q_r.json().get("results", [])))
print(textwrap.shorten(q_r.text, 300))
