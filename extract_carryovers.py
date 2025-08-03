import requests
from bs4 import BeautifulSoup
from datetime import datetime
import os

# 테스트용 날짜 고정 (結果発表日 비교용)
today = "2025.08.02"

# 종목 이름 순서 (HTML 상 등장 순서 기준)
lottery_names = ["BIG", "MEGA BIG", "100円BIG", "BIG1000", "mini BIG"]

# GitHub 설정
github_repo = os.getenv("GITHUB_REPOSITORY")
github_token = os.getenv("GITHUB_TOKEN")
github_assignees = ["Koony2510"]
github_mentions = ["Koony2510"]

# HTML 다운로드
url = "http://www.toto-dream.com/dci/I/IPB/IPB02.do?op=initLotResultDetBIG&popupDispDiv=disp"
response = requests.get(url)
soup = BeautifulSoup(response.text, "html.parser")

# 결과 저장용
results = []

# 5개 섹션 분할: '販売期間' 테이블을 기준으로 자르기
sections = soup.find_all("table", class_="format1 mb5")
carryover_sections = []
for table in sections:
    if "結果発表日" in table.text:
        if today in table.text:
            # 이 테이블 이후에 있는 kobetsu-format2가 이 종목의 당첨금 내역임
            carryover_sections.append(table)

# 결과발표일이 맞는 섹션이 없으면 종료
if not carryover_sections:
    print("✅ 해당 날짜에는 이월금이 없습니다.")
    exit(0)

# 해당 섹션마다 다음에 등장하는 kobetsu-format2 테이블 추출
all_tables = soup.find_all("table")
matched_tables = []
for i, table in enumerate(all_tables):
    if table in carryover_sections:
        # 이 이후에 나오는 kobetsu-format2가 당첨금 테이블
        for j in range(i+1, len(all_tables)):
            if "次回への繰越金" in all_tables[j].text:
                matched_tables.append(all_tables[j])
                break

# 추출된 테이블 기반 결과 파싱
for i, table in enumerate(matched_tables):
    rows = table.find_all("tr")
    if not rows:
        continue
    header = [th.text.strip() for th in rows[0].find_all("th")]
    data_rows = []
    carryover_amount = None
    for row in rows[1:]:
        cols = row.find_all(["td", "th"])
        cols_text = [c.text.strip() for c in cols]
        if len(cols_text) == 4:
            if "1等" in cols_text[0]:
                carryover_amount = cols_text[3]
            if "1等" in cols_text[0] or "2等" in cols_text[0] or "3等" in cols_text[0]:
                data_rows.append(cols_text)
    if carryover_amount and carryover_amount != "0円":
        results.append({
            "name": lottery_names[i],
            "carryover": carryover_amount,
            "rows": data_rows
        })

# 이월금이 없으면 종료
if not results:
    print("✅ 해당 날짜에는 이월금이 없습니다.")
    exit(0)

# Markdown 테이블 생성
def format_table(rows):
    header = "| 등수 | 당첨금 | 당첨수 | 이월금 |\n|---|---|---|---|"
    lines = [header]
    for r in rows:
        line = "| " + " | ".join(r) + " |"
        lines.append(line)
    return "\n".join(lines)

# 금액 포맷 정리
def format_amount(amount):
    num = int(amount.replace("円", "").replace(",", ""))
    if num >= 100_000_000:
        return f"{num // 100_000_000}億円"
    elif num >= 10_000_000:
        return f"{num // 10_000_000}千万円"
    elif num >= 1_000_000:
        return f"{num // 1_000_000}万円"
    elif num >= 10_000:
        return f"{num // 10_000}千円"
    else:
        return f"{num}円"

# 이슈 제목 만들기
issue_title_parts = []
for item in results:
    formatted = format_amount(item["carryover"])
    issue_title_parts.append(f'{item["name"]} {formatted}移越発生')
issue_title = " / ".join(issue_title_parts)

# 이슈 내용 만들기
issue_body = ""
for item in results:
    table_md = format_table(item["rows"])
    issue_body += f"### {item['name']}（{item['carryover']}）\n{table_md}\n\n"

issue_body += "---\n[출처 링크](http://www.toto-dream.com/dci/I/IPB/IPB02.do?op=initLotResultDetBIG&popupDispDiv=disp)"

# GitHub 이슈 생성
if github_repo and github_token:
    api_url = f"https://api.github.com/repos/{github_repo}/issues"
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json"
    }
    mentions = " ".join([f"@{m}" for m in github_mentions])
    payload = {
        "title": issue_title,
        "body": f"{mentions}\n\n{issue_body}",
        "assignees": github_assignees
    }
    response = requests.post(api_url, headers=headers, json=payload)
    if response.status_code == 201:
        print("📌 GitHub 이슈가 성공적으로 생성되었습니다.")
    else:
        print(f"⚠️ GitHub 이슈 생성 실패: {response.status_code} - {response.text}")
else:
    print("⚠️ GITHUB_REPOSITORY 또는 GITHUB_TOKEN 환경변수가 누락되었습니다.")
