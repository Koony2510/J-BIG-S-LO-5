from bs4 import BeautifulSoup
import requests
from datetime import datetime
import os

# 오늘 날짜를 'YYYY.MM.DD' 형식으로 설정 (또는 테스트용으로 고정)
target_date = "2025.08.02"
# target_date = "2025.08.02"  # 테스트용 고정 날짜
# target_date = datetime.today().strftime("%Y.%m.%d") # 당일날짜


# GitHub 설정
github_repo = os.getenv("GITHUB_REPOSITORY")
github_token = os.getenv("GITHUB_TOKEN")
github_assignees = ["Koony2510"]
github_mentions = ["Koony2510"]

# 로또 웹사이트 URL (BIG 시리즈용)
url = "http://www.toto-dream.com/dci/I/IPB/IPB02.do?op=initLotResultDetBIG&popupDispDiv=disp"
response = requests.get(url)
soup = BeautifulSoup(response.content, "html.parser")

# 섹션 구분 기준: '販売期間' 테이블 → 그 다음 'kobetsu-format2' 테이블을 연결
sections = []
for date_table in soup.find_all("table", class_="format1 mb5"):
    if "結果発表日" in date_table.text:
        result_date_td = date_table.find_all("td")[-1]
        result_date_text = result_date_td.get_text(strip=True)
        # '2025年08月02日(土)' → '2025.08.02'
        formatted_date = result_date_text.replace("年", ".").replace("月", ".").split("日")[0]
        sections.append((formatted_date, date_table))

# 모든 kobetsu-format2 추출
all_tables = soup.find_all("table", class_="kobetsu-format2 mb10")

print(f"\n📊 총 감지된 결과발표일 섹션 수: {len(sections)}")
print(f"📊 총 감지된 당첨결과 테이블 수: {len(all_tables)}\n")

lottery_names = ["BIG", "MEGA BIG", "100円BIG", "BIG1000", "mini BIG"]
carryover_results = []
table_index = 0

for i, (date_str, _) in enumerate(sections):
    if date_str != target_date:
        continue  # 날짜가 일치하지 않으면 스킵

    if table_index >= len(all_tables):
        continue

    table = all_tables[table_index]
    rows = table.find_all("tr")

    print(f"\n🧩 [{lottery_names[i]}] 結果発表日: {date_str}")
    found = False
    carryover_amount = ""
    round_name = ""

    for row in rows:
        cols = row.find_all(["th", "td"])
        texts = [c.get_text(strip=True) for c in cols]
        print(" | ".join(texts))

        if not round_name and len(texts) >= 1 and "第" in texts[0] and "回" in texts[0]:
            round_name = texts[0]

        if len(texts) >= 4 and "1等" in texts[0]:
            carryover_amount = texts[3]
            if carryover_amount != "0円":
                found = True

    if found:
        amount = carryover_amount
        amount_num = int(amount.replace(",", "").replace("円", ""))
        if amount_num >= 100000000:
            short = f"{amount_num // 100000000}億円"
        elif amount_num >= 10000000:
            short = f"{amount_num // 1000000}万円"
        else:
            short = f"{amount_num // 10000}万円"

        carryover_results.append({
            "name": lottery_names[i],
            "amount": amount,
            "short": short,
            "table": table,
            "round": round_name or "第????回"
        })

    table_index += 1

# 이월금 결과 정리 및 이슈 생성
if carryover_results:
    issue_title = " / ".join(
        [f"{item['round']} {item['name']} {item['short']} 移越発生" for item in carryover_results]
    )

    body_lines = []
    for item in carryover_results:
        body_lines.append(f"### 🎯 {item['round']} {item['name']} (次回への繰越金: {item['amount']})")
        rows = item["table"].find_all("tr")
        body_lines.append("| 등수 | 당첨금 | 당첨수 | 次回への繰越金 |")
        body_lines.append("|------|--------|--------|----------------|")

        for row in rows:
            cols = row.find_all(["th", "td"])
            texts = [c.get_text(strip=True) for c in cols]
            if len(texts) == 4 and "等" in texts[0]:
                body_lines.append("| " + " | ".join(texts) + " |")
        body_lines.append("")

    body_lines.append("📎 출처: [スポーツくじ公式サイト (BIG)](http://www.toto-dream.com/dci/I/IPB/IPB02.do?op=initLotResultDetBIG&popupDispDiv=disp)")

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

        response = requests.post(
            f"https://api.github.com/repos/{github_repo}/issues",
            headers=headers,
            json=payload
        )

        if response.status_code == 201:
            print("\n✅ GitHub 이슈가 성공적으로 생성되었습니다.")
        else:
            print(f"\n⚠️ GitHub 이슈 생성 실패: {response.status_code} - {response.text}")
    else:
        print("\n⚠️ 환경변수 GITHUB_REPOSITORY 또는 GITHUB_TOKEN 이 설정되지 않았습니다.")
else:
    print("\n✅ 해당 날짜에는 이월금이 없습니다.")
