from playwright.sync_api import sync_playwright
import time

url = "https://www.flashscore.com/match/football/4fpHHhtQ/#/match-summary/match-summary"

def scrape_live_match():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        page.goto(url, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(5000)  # wait for JS to fully load

        previous_events = set()
        previous_home_score = None
        previous_away_score = None
        previous_timer = None
        previous_home_team = None
        previous_away_team = None

        while True:
            # Get team names
            home_team_el = page.query_selector('.duelParticipant__home .participant__participantName')
            away_team_el = page.query_selector('.duelParticipant__away .participant__participantName')

            home_team = home_team_el.inner_text().strip() if home_team_el else "N/A"
            away_team = away_team_el.inner_text().strip() if away_team_el else "N/A"

            # Get match status (e.g. "2nd half")
            status_el = page.query_selector('span.fixedHeaderDuel__detailStatus')
            status_text = status_el.inner_text().strip() if status_el else ""

            # Get current minute/time (last eventTime span)
            event_times = page.query_selector_all('div.eventAndAddedTime > span.eventTime')
            minute_text = event_times[-1].inner_text().strip() if event_times else ""

            # Combine timer display
            if status_text and minute_text:
                timer = f"{status_text} {minute_text}'"
            elif status_text:
                timer = status_text
            elif minute_text:
                timer = f"{minute_text}'"
            else:
                timer = "N/A"

            # Get current score
            score_wrapper = page.query_selector('.detailScore__wrapper.detailScore__live')
            if score_wrapper:
                spans = score_wrapper.query_selector_all('span')
                if len(spans) >= 3:
                    home_score = spans[0].inner_text().strip()
                    away_score = spans[2].inner_text().strip()
                else:
                    home_score = away_score = "N/A"
            else:
                home_score = away_score = "N/A"

            # Get live events (e.g. goals, cards, substitutions)
            event_elements = page.query_selector_all('.event__incident')
            current_events = set()
            for event in event_elements:
                text = event.inner_text().strip()
                current_events.add(text)

            # Detect changes
            changed = False

            if (home_team != previous_home_team) or (away_team != previous_away_team):
                print(f"Teams: {home_team} vs {away_team}")
                previous_home_team = home_team
                previous_away_team = away_team
                changed = True

            if timer != previous_timer:
                print(f"Time: {timer}")
                previous_timer = timer
                changed = True

            if (home_score != previous_home_score) or (away_score != previous_away_score):
                print(f"Score: {home_score} - {away_score}")
                previous_home_score = home_score
                previous_away_score = away_score
                changed = True

            # Detect new events
            new_events = current_events - previous_events
            if new_events:
                print("New events:")
                for ev in new_events:
                    print(f" - {ev}")
                changed = True

            previous_events = current_events

            if not changed:
                print("No changes...")

            time.sleep(30)

if __name__ == "__main__":
    scrape_live_match()
