import re
import os
import requests
from bs4 import BeautifulSoup

# GitHub 사용자 지정
github_assignees = ["Koony2510"]
github_mentions = ["Koony2510"]

def shorten_amount_jpy(amount: int) -> str:
    if amount >= 100_000_000:
        return f"{amount // 100_000_000}億円"
    elif amount >= 10_000:
        return f"{amount // 10_000}万円"
    else:
        return f"{amount:,}円"

def format_table_with_alignment(table_data, headers):
    col_widths = [len(header) for header in headers]
    for row in table_data:
        for i, cell in enumerate(row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], len(cell))
            else:
                col_widths.append(len(cell))

    def pad(row):
        return [cell.ljust(col_widths[i]) for i, cell in enumerate(row)]

    header_line = "| " + " | ".join(pad(headers)) + " |"
    separator_line = "|-" + "-|-".join("-" * w for w in col_widths) + "-|"
    data_lines = ["| " + " | ".join(pad(row)) + " |" for row in table_data]
    return "\n".join([header_line, separator_line] + data_lines)

def extract_and_create_issue(filepath, today):
    section_names = ["BIG", "MEGA BIG", "100円BIG", "BIG1000", "miniBIG"]
    source_url = "http://www.toto-dream.com/dci/I/IPB/IPB02.do?op=initLotResultDetBIG&popupDispDiv=disp"
    with open(filepath, encoding="utf-8") as f:
        html = f.read()
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table")

    results = []
    carry_count = 0
    for table in tables:
        if "次回への繰越金" in table.get_text() and "1等" in table.get_text():
            rows = table.find_all("tr")
            found = False
            table_data = []
            full_amount = 0
            for row in rows:
                ths = row.find_all("th")
                tds = row.find_all("td")
                if ths and "1等" in ths[0].get_text():
                    if len(tds) >= 3:
                        carry_td = tds[2]
                        match = re.search(r"([\d,]+)円", carry_td.get_text())
                        if match:
                            full_amount = int(match.group(1).replace(",", ""))
                            if full_amount > 0 and carry_count < len(section_names):
                                section_name = section_names[carry_count]
                                carry_count += 1
                                found = True

                if found and (ths and any("等" in th.get_text() for th in ths)):
                    th_text = ths[0].get_text(strip=True)
                    td_texts = [td.get_text(strip=True) for td in tds]
                    table_data.append([th_text] + td_texts)
                if found and len(table_data) >= 3:
                    break

            if found and full_amount:
                headers = ["等級", "当せん金", "当せん口数", "次回への繰越金"]
                table_markdown = format_table_with_alignment(table_data, headers)
                short_amount = shorten_amount_jpy(full_amount)
                results.append((section_name, short_amount, table_markdown))
        if carry_count >= len(section_names):
            break

    if results:
        title = " / ".join(f"{name} {amt} 繰越発生" for name, amt, _ in results)
        body = "\n\n".join(f"### {name}\n{table}" for name, amt, table in results)
        mention_text = " ".join([f"@{m}" for m in github_mentions])
        body += f"\n\n---\n{mention_text}\n出典：[スポーツくじ公式サイト]({source_url})"

        # GitHub 이슈 자동 생성
        github_repo = os.getenv("GITHUB_REPOSITORY")
        github_token = os.getenv("GITHUB_TOKEN")
        if github_repo and github_token:
            api_url = f"https://api.github.com/repos/{github_repo}/issues"
            headers = {
                "Authorization": f"Bearer {github_token}",
                "Accept": "application/vnd.github+json"
            }
            payload = {
                "title": title,
                "body": body,
                "assignees": github_assignees
            }
            response = requests.post(api_url, headers=headers, json=payload)
            if response.status_code == 201:
                print("📌 GitHub 이슈가 성공적으로 생성되었습니다.")
            else:
                print(f"⚠️ GitHub 이슈 생성 실패: {response.status_code} - {response.text}")
        else:
            print("⚠️ GITHUB 환경변수(GITHUB_REPOSITORY, GITHUB_TOKEN)가 누락되었습니다.")
    else:
        print("✅ 해당 날짜에는 이월금이 없습니다.")

if __name__ == "__main__":
    extract_and_create_issue("toto_debug.html", "2025年08月02日")
