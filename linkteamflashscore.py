import time
import csv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

URL = "https://www.flashscore.com/standings/fgzlZk5U/6HCkYDZ1/#/6HCkYDZ1/standings/overall/"

options = webdriver.ChromeOptions()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

try:
    driver.get(URL)
    time.sleep(5)  # wait for JS to load

    teams_data = []

    rows = driver.find_elements(By.CSS_SELECTOR, 'div.tableCellParticipant__block')

    for row in rows:
        try:
            link_el = row.find_element(By.CSS_SELECTOR, 'a')
            name = row.text.strip()  # ✅ use row.text instead of link_el.text
            link = link_el.get_attribute("href")
            logo = row.find_element(By.CSS_SELECTOR, 'img').get_attribute("src")

            teams_data.append([name, link, logo])
        except Exception as e:
            print("Skipping row due to error:", e)

    with open("tunisian_league_teams.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Team Name", "Team Link", "Team Logo"])
        writer.writerows(teams_data)

    print("✅ CSV file 'tunisian_league_teams.csv' updated successfully!")

finally:
    driver.quit()
