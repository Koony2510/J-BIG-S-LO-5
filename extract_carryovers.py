from bs4 import BeautifulSoup
from datetime import datetime
import requests
import os
import re

def normalize_date(raw_date: str) -> str:
    return re.sub(r"\(.*?\)", "", raw_date).strip()

def format_money_for_title(money: str) -> str:
    money_num = int(money.replace(",", "").replace("円", ""))
    if money_num >= 10**8:
        return f"{money_num // 10**8}億円"
    elif money_num >= 10**6:
        return f"{money_num // 10**4}万円"
    else:
        return f"{money_num}円"

def extract_carryovers_by_resultdate(html_path: str, today: str):
    with open(html_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    today_norm = normalize_date(today)
    lot_names = ["BIG", "MEGA BIG", "100円BIG", "BIG1000", "mini BIG"]
    sections = soup.find_all("table", class_="kobetsu-format2")
    result_tables = soup.find_all("table", class_="format1")

    results = []
    lot_idx = 0

    for section in sections:
        result_date = None
        for tbl in result_tables:
            headers = tbl.find_all("th")
            if any("結果発表日" in h.text for h in headers):
                date_tds = tbl.find_all("td")
                if len(date_tds) >= 3:
                    result_date_raw = date_tds[2].text.strip()
                    result_date = normalize_date(result_date_raw)
                    result_tables.remove(tbl)
                    break

        if result_date != today_norm:
            lot_idx += 1
            continue

        rows = section.find_all("tr")
        title_row = rows[0].find_all("th")
        if len(title_row) < 4 or "次回への繰越金" not in title_row[3].text:
            lot_idx += 1
            continue

        carryover_row = None
        for row in rows[1:]:
            cols = row.find_all(["th", "td"])
            if len(cols) == 4 and "1等" in cols[0].text:
                carryover_row = cols
                break

        if not carryover_row:
            lot_idx += 1
            continue

        carryover = carryover_row[3].text.strip()
        if carryover != "0円":
            summary_md = "| 等級 | 当せん金 | 口数 | 繰越金 |\n|---|---|---|---|\n"
            for row in rows[1:4]:
                cols = row.find_all(["th", "td"])
                if len(cols) == 4:
                    summary_md += f"| {cols[0].text.strip()} | {cols[1].text.strip()} | {cols[2].text.strip()} | {cols[3].text.strip()} |\n"

            results.append({
                "name": lot_names[lot_idx],
                "carryover": carryover,
                "summary_md": summary_md,
                "result_date": result_date
            })

        lot_idx += 1

    if not results:
        print("✅ 해당 날짜에는 이월금이 없습니다.")
        return

    title = " / ".join([
        f"{r['name']} {format_money_for_title(r['carryover'])} 繰越発生"
        for r in results
    ])

    body = "\n\n".join([f"### {r['name']}（{r['result_date']}）\n{r['summary_md']}" for r in results])
    body += "\n\n---\n出典：[スポーツくじ公式サイト](http://www.toto-dream.com/dci/I/IPB/IPB02.do?op=initLotResultDetBIG&popupDispDiv=disp)"

    github_repo = os.getenv("GITHUB_REPOSITORY")
    github_token = os.getenv("GITHUB_TOKEN")
    github_assignees = ["Koony2510"]
    github_mentions = ["Koony2510"]

    if github_repo and github_token:
        api_url = f"https://api.github.com/repos/{github_repo}/issues"
        headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github+json"
        }
        mention_text = " ".join([f"@{user}" for user in github_mentions])
        payload = {
            "title": title,
            "body": f"{mention_text}\n\n{body}",
            "assignees": github_assignees
        }
        response = requests.post(api_url, headers=headers, json=payload)
        if response.status_code == 201:
            print("📌 GitHub 이슈가 성공적으로 생성되었습니다.")
        else:
            print(f"⚠️ GitHub 이슈 생성 실패: {response.status_code} - {response.text}")
    else:
        print("⚠️ GITHUB_REPOSITORY 또는 GITHUB_TOKEN 환경변수가 설정되어 있지 않습니다.")

if __name__ == "__main__":
    today_jp = datetime.today().strftime("%Y年%m月%d日")
    extract_carryovers_by_resultdate("toto_debug.html", today_jp)
