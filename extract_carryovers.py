from bs4 import BeautifulSoup
import requests
from datetime import datetime
import os
import re

# 오늘 날짜를 'YYYY.MM.DD' 형식으로 설정 (혹은 고정값으로 테스트)
target_date = datetime.today().strftime("%Y.%m.%d")
# target_date = "2025.08.02"  # 테스트용 고정값
# target_date = datetime.today().strftime("%Y.%m.%d")

# GitHub 설정
github_repo = os.getenv("GITHUB_REPOSITORY")
github_token = os.getenv("GITHUB_TOKEN")
github_assignees = ["Koony2510"]
github_mentions = ["Koony2510"]

# 로또 웹사이트 URL
url = "http://www.toto-dream.com/dci/I/IPB/IPB02.do?op=initLotResultDetBIG&popupDispDiv=disp"
response = requests.get(url)
soup = BeautifulSoup(response.content, "html.parser")

# 결과 발표일 섹션 추출
sections = []
for date_table in soup.find_all("table", class_="format1 mb5"):
    if "結果発表日" in date_table.text:
        result_date_td = date_table.find_all("td")[-1]
        result_date_text = result_date_td.get_text(strip=True)
        formatted_date = result_date_text.replace("年", ".").replace("月", ".").split("日")[0]
        sections.append((formatted_date, date_table))

# 모든 결과 테이블 추출
all_tables = soup.find_all("table", class_="kobetsu-format2 mb10")

print(f"\n📊 총 감지된 결과발표일 섹션 수: {len(sections)}")
print(f"📊 총 감지된 당첨결과 테이블 수: {len(all_tables)}\n")

lottery_names = ["BIG", "MEGA BIG", "100円BIG", "BIG1000", "mini BIG"]
carryover_results = []
table_index = 0

for i, (date_str, _) in enumerate(sections):
    if date_str != target_date:
        continue

    if table_index >= len(all_tables):
        continue

    table = all_tables[table_index]
    rows = table.find_all("tr")

    print(f"\n🧩 [{lottery_names[i]}] 結果発表日: {date_str}")
    found = False
    carryover_amount = ""

    # 회차 정보 추출 (이전 요소들에서 검색)
    round_number = "不明"
    for elem in table.previous_elements:
        if elem.name in ["td", "th", "div", "p", "span"] and elem.string:
            match = re.search(r"第(\d+)回", elem.string.strip())
            if match:
                round_number = f"第{match.group(1)}回"
                break

    for row in rows:
        cols = row.find_all(["th", "td"])
        texts = [c.get_text(strip=True) for c in cols]
        print(" | ".join(texts))

        if len(texts) >= 4 and "1等" in texts[0]:
            carryover_amount = texts[3]
            if carryover_amount != "0円":
                found = True

    if found:
        amount = carryover_amount
        amount_num = int(amount.replace(",", "").replace("円", ""))
        if amount_num >= 100000000:
            short = f"{amount_num // 100000000}億円"
        else:
            short = f"{amount_num // 10000}万円"

        # 마크다운 표 정리
        body_table = []
        body_table.append("| 등수 | 당첨금 | 당첨수 | 次回への繰越金 |")
        body_table.append("|------|--------|--------|----------------|")
        for row in rows:
            cols = row.find_all(["th", "td"])
            texts = [c.get_text(strip=True) for c in cols]
            if len(texts) == 4 and "等" in texts[0]:
                body_table.append("| " + " | ".join(texts) + " |")

        carryover_results.append({
            "name": lottery_names[i],
            "amount": amount,
            "short": short,
            "round": round_number,
            "table_lines": body_table
        })

    table_index += 1

# 이월금 존재 시 GitHub 이슈 생성
if carryover_results:
    # 회차 모두 동일하면 한 번만 표시
    rounds = set(item["round"] for item in carryover_results)
    if len(rounds) == 1:
        title_prefix = list(rounds)[0]
        issue_title = title_prefix + " " + " / ".join([f"{item['name']} {item['short']} 移越発生" for item in carryover_results])
    else:
        issue_title = " / ".join([f"{item['round']} {item['name']} {item['short']} 移越発生" for item in carryover_results])

    # 본문 생성
    body_lines = []
    for item in carryover_results:
        body_lines.append(f"### 🎯 {item['round']} {item['name']} (次回への繰越金: {item['amount']})")
        body_lines.extend(item["table_lines"])
        body_lines.append("")

    body_lines.append("📎 出処: [スポーツくじ公式サイト](http://www.toto-dream.com/dci/I/IPB/IPB02.do?op=initLotResultDetBIG&popupDispDiv=disp)")

    # GitHub 이슈 POST
    if github_repo and github_token:
        headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github+json"
        }
        payload = {
            "title": issue_title,
            "body": f"{' '.join([f'@{u}' for u in github_mentions])}\n\n" + "\n".join(body_lines),
            "assignees": github_assignees
        }
        r = requests.post(f"https://api.github.com/repos/{github_repo}/issues", headers=headers, json=payload)
        if r.status_code == 201:
            print("\n✅ GitHub 이슈가 성공적으로 생성되었습니다.")
        else:
            print(f"\n⚠️ GitHub 이슈 생성 실패: {r.status_code} - {r.text}")
    else:
        print("\n⚠️ 환경변수 GITHUB_REPOSITORY 또는 GITHUB_TOKEN 이 설정되지 않았습니다.")
else:
    print("\n✅ 해당 날짜에는 이월금이 없습니다.")
