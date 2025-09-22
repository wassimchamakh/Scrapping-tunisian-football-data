import requests
from bs4 import BeautifulSoup
import csv
import time
import random
from urllib.parse import urljoin
from datetime import datetime
import re

# Configuration
club_id = 3342
test_year = 2019  # Testing with 2019 season
current_year = datetime.now().year

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

def get_club_country_from_url(club_url, debug=False):
    """Extract club country from club page"""
    if not club_url or 'verein/515' in club_url or 'verein/123' in club_url:
        return ""
    
    try:
        response = requests.get(club_url, headers=HEADERS, timeout=8)
        if response.status_code != 200:
            return ""
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for country flag in club header
        flag_imgs = soup.find_all('img')
        for img in flag_imgs:
            img_src = img.get('src', '').lower()
            img_title = img.get('title', '').strip()
            
            if ('flagge' in img_src or 'flag' in img_src) and img_title and len(img_title) > 1:
                if debug:
                    print(f"        🌍 Club country found: {img_title}")
                return img_title
        
        time.sleep(random.uniform(0.1, 0.3))
        return ""
        
    except Exception as e:
        if debug:
            print(f"        ❌ Error fetching club country: {e}")
        return ""

def get_comprehensive_club_info(player_url, debug=False):
    """Get comprehensive current club information with exhaustive detection methods"""
    if not player_url:
        return {}, ""
    
    try:
        if debug:
            print(f"        🔍 Fetching comprehensive club info from: {player_url[:50]}...")
        
        response = requests.get(player_url, headers=HEADERS, timeout=15)
        if response.status_code != 200:
            return {}, ""
        
        soup = BeautifulSoup(response.text, 'html.parser')
        details = {}
        current_club = ""
        
        # Method 1: Data header club (most reliable when present)
        club_link = soup.select_one('.data-header__club a[href*="/verein/"]')
        if club_link and club_link.get('href') and 'verein/515' not in club_link.get('href'):
            current_club = club_link.get_text(strip=True)
            club_url = urljoin("https://www.transfermarkt.com", club_link['href'])
            details['current_club_url'] = club_url
            if debug:
                print(f"        🏟️ Current club (method 1 - data header): {current_club}")
        
        # Method 2: Look for any club links in the entire page content
        if not current_club:
            all_club_links = soup.find_all('a', href=lambda x: x and '/verein/' in x and '/startseite' in x)
            recent_clubs = []
            
            for link in all_club_links:
                href = link.get('href', '')
                club_name = link.get_text(strip=True)
                
                # Skip generic links
                if ('verein/515' in href or 'verein/123' in href or 
                    not club_name or len(club_name) < 2 or
                    club_name.lower() in ['club', 'verein', 'team']):
                    continue
                
                # Check if this club appears in a recent context
                parent_text = ""
                parent = link.find_parent()
                if parent:
                    parent_text = parent.get_text().lower()
                
                # Look for indicators of current/recent club
                recent_indicators = ['current', '2024', '2025', 'since', 'joined', 'contract']
                is_recent = any(indicator in parent_text for indicator in recent_indicators)
                
                if is_recent or not recent_clubs:  # First club found or recent club
                    recent_clubs.append((club_name, href, is_recent))
            
            # Prefer recent clubs, otherwise take the first one
            if recent_clubs:
                recent_clubs.sort(key=lambda x: x[2], reverse=True)  # Sort by is_recent
                current_club = recent_clubs[0][0]
                club_url = urljoin("https://www.transfermarkt.com", recent_clubs[0][1])
                details['current_club_url'] = club_url
                if debug:
                    print(f"        🏟️ Current club (method 2 - page scan): {current_club}")
        
        # Method 3: Check transfer history for most recent incoming transfer
        if not current_club:
            transfer_tables = soup.find_all('table', class_='items')
            for table in transfer_tables:
                rows = table.find_all('tr')
                for row in rows[:5]:  # Check first few rows
                    cols = row.find_all('td')
                    if len(cols) >= 4:
                        # Look for transfer direction indicators
                        for col in cols:
                            img = col.find('img')
                            if img and img.get('title'):
                                img_title = img.get('title').lower()
                                # Look for "joined" or incoming transfer indicators
                                if 'joined' in img_title or 'free transfer' in img_title:
                                    # Find club in the same row
                                    for search_col in cols:
                                        club_link = search_col.find('a', href=lambda x: x and '/verein/' in x)
                                        if club_link and 'verein/515' not in club_link.get('href', ''):
                                            current_club = club_link.get_text(strip=True)
                                            club_url = urljoin("https://www.transfermarkt.com", club_link['href'])
                                            details['current_club_url'] = club_url
                                            if debug:
                                                print(f"        🏟️ Current club (method 3 - transfers): {current_club}")
                                            break
                                    if current_club:
                                        break
                        if current_club:
                            break
                if current_club:
                    break
        
        # Method 4: Look in performance/stats tables for current season
        if not current_club:
            perf_tables = soup.find_all('table', class_='items')
            current_seasons = ['24/25', '2024', '2025']
            
            for table in perf_tables:
                rows = table.find_all('tr')
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 2:
                        season_text = cols[0].get_text(strip=True)
                        if any(season in season_text for season in current_seasons):
                            club_cell = cols[1]
                            club_link = club_cell.find('a', href=lambda x: x and '/verein/' in x)
                            if club_link and 'verein/515' not in club_link.get('href', ''):
                                current_club = club_link.get_text(strip=True)
                                club_url = urljoin("https://www.transfermarkt.com", club_link['href'])
                                details['current_club_url'] = club_url
                                if debug:
                                    print(f"        🏟️ Current club (method 4 - performance): {current_club}")
                                break
                if current_club:
                    break
        
        # Method 5: Look for any recent club mentions in text
        if not current_club:
            page_text = soup.get_text()
            
            # Look for patterns like "Since 2024: Club Name" or "Current club: Club Name"
            patterns = [
                r'since\s+202[4-5].*?([A-Z][a-zA-Z\s]+)',
                r'current club.*?([A-Z][a-zA-Z\s]+)',
                r'joined.*?202[4-5].*?([A-Z][a-zA-Z\s]+)',
                r'contract.*?([A-Z][a-zA-Z\s]+)'
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                for match in matches:
                    if len(match.strip()) > 2 and match.strip() not in ['Without Club', 'Retired']:
                        # Verify this might be a club name by checking if it appears as a link
                        potential_club = match.strip()
                        club_link = soup.find('a', string=re.compile(re.escape(potential_club), re.I))
                        if club_link and '/verein/' in club_link.get('href', ''):
                            current_club = potential_club
                            club_url = urljoin("https://www.transfermarkt.com", club_link['href'])
                            details['current_club_url'] = club_url
                            if debug:
                                print(f"        🏟️ Current club (method 5 - text analysis): {current_club}")
                            break
                if current_club:
                    break
        
        # Check for retirement/without club status only if no club found
        if not current_club:
            page_text = soup.get_text().lower()
            if 'retired' in page_text or 'career end' in page_text:
                current_club = "Retired"
                details['current_club_url'] = "https://www.transfermarkt.com/retired/startseite/verein/123"
                if debug:
                    print(f"        🚫 Status detected: Retired")
            elif 'without club' in page_text or 'vereinslos' in page_text:
                current_club = "Without Club"
                details['current_club_url'] = "https://www.transfermarkt.com/vereinslos/startseite/verein/515"
                if debug:
                    print(f"        🚫 Status detected: Without Club")
        
        # Extract club logo if we have a club
        if details.get('current_club_url') and current_club not in ["Retired", "Without Club"]:
            logo_selectors = [
                '.data-header__club img',
                'img[src*="wappen"]',
                'img[src*="vereinslogo"]'
            ]
            
            for selector in logo_selectors:
                logo_img = soup.select_one(selector)
                if logo_img and logo_img.get('src'):
                    logo_src = logo_img.get('src')
                    if 'wappen' in logo_src or 'vereinslogo' in logo_src:
                        logo_url = urljoin("https://www.transfermarkt.com", logo_src)
                        details['current_club_logo'] = logo_url
                        if debug:
                            print(f"        🎨 Club logo found: {logo_url[:50]}...")
                        break
        
        # Get club country
        if details.get('current_club_url') and current_club not in ["Retired", "Without Club"]:
            club_country = get_club_country_from_url(details['current_club_url'], debug)
            if club_country:
                details['current_club_country'] = club_country
        
        time.sleep(random.uniform(0.5, 1.0))
        return details, current_club
        
    except Exception as e:
        if debug:
            print(f"        ❌ Error fetching comprehensive club info: {e}")
        return {}, ""

def get_player_detailed_info(player_url, debug=False):
    """Fetch detailed information from player's profile page"""
    if not player_url:
        return {}
    
    try:
        response = requests.get(player_url, headers=HEADERS, timeout=15)
        if response.status_code != 200:
            return {}
        
        soup = BeautifulSoup(response.text, 'html.parser')
        details = {}
        
        # Extract height
        height_section = soup.find('span', string=re.compile(r'Height', re.I))
        if height_section:
            height_value = height_section.find_next('span')
            if height_value:
                height_text = height_value.get_text(strip=True)
                if 'm' in height_text and any(c.isdigit() for c in height_text):
                    details['height'] = height_text
                    if debug:
                        print(f"        📏 Height: {height_text}")
        
        # Extract player image
        img_selectors = [
            'img[data-src*="portrait/header"]',
            'img[src*="portrait/header"]',
            'img[data-src*="portrait/medium"]',
            'img[src*="portrait/medium"]'
        ]
        
        for selector in img_selectors:
            img = soup.select_one(selector)
            if img:
                img_src = img.get('data-src') or img.get('src')
                if img_src and 'data:image' not in img_src and 'default' not in img_src:
                    full_img_url = urljoin("https://www.transfermarkt.com", img_src)
                    details['player_image'] = full_img_url
                    if debug:
                        print(f"        📸 Player image found")
                    break
        
        time.sleep(random.uniform(0.2, 0.4))
        return details
        
    except Exception as e:
        if debug:
            print(f"        ❌ Error fetching player details: {e}")
        return {}

def extract_jersey_number(cols, debug=False):
    """Extract jersey number from the squad table"""
    for col_index in range(min(4, len(cols))):
        col_text = cols[col_index].get_text(strip=True)
        if col_text.isdigit() and 1 <= int(col_text) <= 99:
            return col_text
    return ""

def extract_age_from_table(cols, debug=False):
    """Extract player age from the table"""
    for col_index in range(2, min(8, len(cols))):
        col_text = cols[col_index].get_text(strip=True)
        
        age_patterns = [r'\b(\d{2})\b', r'(\d{2})\s*years?', r'Age:\s*(\d{2})']
        
        for pattern in age_patterns:
            matches = re.findall(pattern, col_text, re.IGNORECASE)
            for match in matches:
                age = int(match)
                if 15 <= age <= 45:
                    return str(age)
    return ""

def extract_nationality_from_table(cols, debug=False):
    """Extract player nationality from flag images"""
    for col in cols:
        flag_imgs = col.find_all('img')
        for img in flag_imgs:
            img_src = img.get('src', '').lower()
            img_title = img.get('title', '').strip()
            
            if ('flagge' in img_src or 'flag' in img_src) and img_title and len(img_title) > 1:
                return img_title
    return ""

def extract_position_from_table(cols, player_name, debug=False):
    """Extract player position from table"""
    position_map = {
        'torwart': 'Goalkeeper', 'goalkeeper': 'Goalkeeper', 'keeper': 'Goalkeeper', 'gk': 'Goalkeeper',
        'innenverteidiger': 'Centre-Back', 'centre-back': 'Centre-Back', 'center-back': 'Centre-Back', 'cb': 'Centre-Back',
        'linksverteidiger': 'Left-Back', 'left-back': 'Left-Back', 'lb': 'Left-Back',
        'rechtsverteidiger': 'Right-Back', 'right-back': 'Right-Back', 'rb': 'Right-Back',
        'defensives mittelfeld': 'Defensive Midfield', 'defensive midfield': 'Defensive Midfield', 'dm': 'Defensive Midfield',
        'zentrales mittelfeld': 'Central Midfield', 'central midfield': 'Central Midfield', 'cm': 'Central Midfield',
        'offensives mittelfeld': 'Attacking Midfield', 'attacking midfield': 'Attacking Midfield', 'am': 'Attacking Midfield',
        'linksaußen': 'Left Winger', 'left winger': 'Left Winger', 'lw': 'Left Winger',
        'rechtsaußen': 'Right Winger', 'right winger': 'Right Winger', 'rw': 'Right Winger',
        'mittelstürmer': 'Centre-Forward', 'centre-forward': 'Centre-Forward', 'cf': 'Centre-Forward',
        'stürmer': 'Striker', 'striker': 'Striker', 'st': 'Striker',
    }
    
    for col_index in range(2, min(8, len(cols))):
        col_text = cols[col_index].get_text(strip=True).lower()
        for keyword, position in position_map.items():
            if keyword in col_text:
                return position
    return ""

def extract_market_value_from_table(cols, debug=False):
    """Extract market value"""
    for col in cols:
        val_text = col.get_text(strip=True)
        if '€' in val_text and any(char.isdigit() for char in val_text):
            cleaned_value = val_text.replace('\n', ' ').replace('\t', ' ')
            cleaned_value = re.sub(r'\s+', ' ', cleaned_value).strip()
            return cleaned_value
    return ""

def fetch_players_for_year_enhanced(year, debug=False):
    """Fetch all players for a specific year with comprehensive data extraction"""
    url = f"https://www.transfermarkt.com/esperance-tunis/kader/verein/{club_id}/saison_id/{year}"
    
    try:
        if debug:
            print(f"  🌐 Fetching {year}/{year+1} season: {url}")
        
        response = requests.get(url, headers=HEADERS, timeout=30)
        if response.status_code != 200:
            print(f"  ❌ HTTP {response.status_code} for year {year}")
            return []
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        table = soup.select_one('table.items')
        if not table:
            print(f"  ❌ No table found for year {year}")
            return []

        players = []
        rows = table.find_all('tr')
        
        data_rows = []
        for row in rows:
            cols = row.find_all(['td', 'th'])
            if len(cols) >= 4:
                has_player_link = any(col.find('a', href=lambda x: x and '/profil/spieler/' in x) for col in cols)
                if has_player_link:
                    data_rows.append(row)
        
        print(f"  📊 Found {len(data_rows)} player rows in table")
        
        for row_index, row in enumerate(data_rows, 1):
            cols = row.find_all(['td', 'th'])
            
            # Extract player name and URL
            player_link = None
            player_name = ""
            
            for col in cols:
                link = col.find('a', href=lambda x: x and '/profil/spieler/' in x)
                if link:
                    player_link = link
                    player_name = link.get_text(strip=True)
                    break
            
            if not player_name:
                continue
                
            if debug:
                print(f"    👤 Processing player {row_index}: {player_name}")
            
            player_url = ""
            if player_link and player_link.get('href'):
                player_url = urljoin("https://www.transfermarkt.com", player_link['href'])

            # Extract basic data from table
            jersey_number = extract_jersey_number(cols, debug)
            age = extract_age_from_table(cols, debug)
            position = extract_position_from_table(cols, player_name, debug)
            nationality = extract_nationality_from_table(cols, debug)
            market_value = extract_market_value_from_table(cols, debug)
            
            # Get detailed information
            player_details = get_player_detailed_info(player_url, debug)
            club_details, current_club = get_comprehensive_club_info(player_url, debug)
            
            # Compile all data
            height = player_details.get('height', '')
            player_image = player_details.get('player_image', '')
            current_club_url = club_details.get('current_club_url', '')
            current_club_logo = club_details.get('current_club_logo', '')
            current_club_country = club_details.get('current_club_country', '')
            
            if not current_club:
                current_club = "Without Club"

            player_data = {
                'Player': player_name,
                'Season': f"{year}/{year+1}",
                'Jersey_Number': jersey_number,
                'Age': age,
                'Height': height,
                'Position': position,
                'Nationality': nationality,
                'Player_Image': player_image,
                'Profile_URL': player_url,
                'Current_Club': current_club,
                'Current_Club_URL': current_club_url,
                'Current_Club_Logo': current_club_logo,
                'Current_Club_Country': current_club_country,
                'Market_Value': market_value
            }
            
            players.append(player_data)
            
            if debug:
                print(f"    ✅ Player {row_index} processed: {current_club}")

        print(f"  ✅ Successfully processed {len(players)} players for {year}/{year+1}")
        return players

    except Exception as e:
        print(f"  ❌ Error fetching year {year}: {e}")
        return []

def main():
    """Main function to test the comprehensive scraper"""
    print(f"🚀 Testing Comprehensive Esperance Tunis Player Scraper v5")
    print(f"📅 Testing with {test_year}/{test_year+1} season")
    print("=" * 60)
    
    players = fetch_players_for_year_enhanced(test_year, debug=True)
    
    if players:
        filename = f'esperance_tunis_comprehensive_v5_{test_year}.csv'
        fieldnames = [
            'Player', 'Season', 'Jersey_Number', 'Age', 'Height', 
            'Position', 'Nationality', 'Player_Image', 'Profile_URL',
            'Current_Club', 'Current_Club_URL', 'Current_Club_Logo', 
            'Current_Club_Country', 'Market_Value'
        ]
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(players)
        
        print(f"\n🎉 Success! Saved {len(players)} players to {filename}")
        
        # Detailed statistics
        actual_clubs = [p for p in players if p['Current_Club'] not in ['Without Club', 'Retired']]
        club_logos = [p for p in players if p['Current_Club_Logo']]
        club_countries = [p for p in players if p['Current_Club_Country']]
        
        print(f"\n📈 ENHANCED DATA COMPLETENESS:")
        print(f"  Total Players: {len(players)}")
        print(f"  Players with Actual Clubs: {len(actual_clubs)}/{len(players)} ({len(actual_clubs)/len(players)*100:.1f}%)")
        print(f"  Club Logos: {len(club_logos)}/{len(players)} ({len(club_logos)/len(players)*100:.1f}%)")
        print(f"  Club Countries: {len(club_countries)}/{len(players)} ({len(club_countries)/len(players)*100:.1f}%)")
        
        print(f"\n🏟️ ALL CURRENT CLUBS FOUND:")
        club_counts = {}
        for p in players:
            club = p['Current_Club']
            club_counts[club] = club_counts.get(club, 0) + 1
        
        for club, count in sorted(club_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  • {club}: {count} players")
        
        print(f"\n✅ PLAYERS WITH IDENTIFIED CLUBS:")
        for player in actual_clubs:
            country_info = f" ({player['Current_Club_Country']})" if player['Current_Club_Country'] else ""
            print(f"  • {player['Player']} → {player['Current_Club']}{country_info}")
        
    else:
        print(f"❌ No players found!")

if __name__ == "__main__":
    main()