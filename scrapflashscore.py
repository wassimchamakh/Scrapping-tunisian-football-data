from playwright.sync_api import sync_playwright
import time

url = "https://www.flashscore.com/team/esperance-tunis/bVINpDMl/fixtures/"

def scrape_fixtures():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page(user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/115.0.0.0 Safari/537.36"
        ))

        page.goto(url, wait_until="networkidle", timeout=90000)
        page.wait_for_timeout(10000)  # wait 10 seconds for JS lazy loading

        try:
            page.click('button#onetrust-accept-btn-handler', timeout=5000)
            print("✅ Accepted cookies")
        except:
            print("ℹ️ No cookie banner found")

        matches = page.query_selector_all('.event__match')
        print(f"Found {len(matches)} matches")

        for i, match in enumerate(matches, 1):
            time_elem = match.query_selector('.event__time')
            time_str = time_elem.inner_text().strip() if time_elem else "No time"

            home_elem = match.query_selector('.event__homeParticipant span')
            away_elem = match.query_selector('.event__awayParticipant span')

            home = home_elem.inner_text().strip() if home_elem else "No home team"
            away = away_elem.inner_text().strip() if away_elem else "No away team"

            if time_str.lower() not in ['live', 'postp.', 'canc.', 'abn.']:
                print(f"Match {i}: {time_str} | {home} vs {away}")

        browser.close()                                  

if __name__ == "__main__":
    scrape_fixtures()
