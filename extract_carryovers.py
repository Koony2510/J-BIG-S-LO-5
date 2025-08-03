from bs4 import BeautifulSoup
from datetime import datetime
import requests
import os
import re

# 결과발표일을 테스트용으로 고정 (운영 시에는 datetime.today().strftime('%Y年%m月%d日') 사용)
today = "2025年08月02日"

# GitHub 설정
GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_ASSIGNEES = ["Koony2510"]
GITHUB_MENTIONS = ["Koony2510"]

# 이월금 금액을 억/만 단위로 축약하는 함수
def shorten_amount(amount_str):
    amount = int(amount_str.replace(",", "").replace("円", ""))
    if amount >= 10_0000_0000:
        return f"{amount // 100_000_000}億円"
    elif amount >= 10_0000:
        return f"{amount // 10_000}万円"
    else:
        return f"{amount}円"

# 웹에서 HTML 가져오기
url = "http://www.toto-dream.com/dci/I/IPB/IPB02.do?op=initLotResultDetBIG&popupDispDiv=disp"
headers = {
    "User-Agent": "Mozilla/5.0"
}
res = requests.get(url, headers=headers)
res.encoding = res.apparent_encoding
html = res.text

# HTML 파싱
soup = BeautifulSoup(html, "html.parser")
sections = soup.find_all("div", class_="contents")

carryover_titles = []
issue_body_parts = []
source_url = url

lottery_names = ["BIG", "MEGA BIG", "100円BIG", "BIG1000", "mini BIG"]
lottery_index = 0

for section in sections:
    result_date_tag = section.find("table", class_="format1 mb5")
    if not result_date_tag:
        continue

    result_date_text = result_date_tag.get_text()
    match = re.search(r"結果発表日.*?(\d{4}年\d{2}月\d{2}日)", result_date_text)
    if not match:
        continue

    result_date = match.group(1).strip()
    if result_date != today:
        continue

    prize_table = section.find("table", class_="kobetsu-format2 mb10")
    if not prize_table:
        continue

    rows = prize_table.find_all("tr")[1:]  # 헤더 제외
    relevant_rows = []
    carryover_amount = None

    for row in rows:
        cols = [col.get_text(strip=True) for col in row.find_all(["th", "td"])]
        if len(cols) != 4:
            continue

        if cols[0] == "1等":
            carryover_amount = cols[3]
            if carryover_amount != "0円":
                carryover_title = f"{lottery_names[lottery_index]} {shorten_amount(carryover_amount)} 繰越発生"
                carryover_titles.append(carryover_title)

        if cols[0] in ["1等", "2等", "3等"]:
            relevant_rows.append(cols)

    if carryover_amount and carryover_amount != "0円":
        table_md = "| 等級 | 当せん金 | 口数 | 繰越金 |\n|---|---|---|---|\n"
        for r in relevant_rows:
            table_md += f"| {' | '.join(r)} |\n"

        block = f"### {lottery_names[lottery_index]}（{result_date}）\n{table_md}"
        issue_body_parts.append(block)

    lottery_index += 1
    if lottery_index >= len(lottery_names):
        break

# GitHub 이슈 생성
if carryover_titles:
    issue_title = " / ".join(carryover_titles)
    mention_text = " ".join([f"@{user}" for user in GITHUB_MENTIONS])
    issue_body = f"{mention_text}\n\n" + "\n\n".join(issue_body_parts)
    issue_body += f"\n\n出典: [{source_url}]({source_url})"

    if GITHUB_REPOSITORY and GITHUB_TOKEN:
        api_url = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/issues"
        headers = {
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json"
        }
        payload = {
            "title": issue_title,
            "body": issue_body,
            "assignees": GITHUB_ASSIGNEES
        }
        response = requests.post(api_url, headers=headers, json=payload)
        if response.status_code == 201:
            print("✅ GitHub 이슈가 성공적으로 생성되었습니다.")
        else:
            print(f"⚠️ GitHub 이슈 생성 실패: {response.status_code} - {response.text}")
    else:
        print("⚠️ GITHUB_REPOSITORY 또는 GITHUB_TOKEN 환경변수가 설정되지 않았습니다.")
else:
    print("✅ 해당 날짜에는 이월금이 없습니다.")
