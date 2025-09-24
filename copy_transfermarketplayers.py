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
start_year = 2012
current_year = datetime.now().year
years_to_scrape = list(range(start_year, current_year + 1))

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Cache-Control": "max-age=0"
}

def create_session():
    """Create a session with proper headers"""
    session = requests.Session()
    session.headers.update(HEADERS)
    return session

def extract_jersey_number(row):
    """Extract jersey number - it's usually in the first column with a number"""
    cols = row.find_all('td')
    
    # Check first 3 columns for jersey number
    for i in range(min(3, len(cols))):
        text = cols[i].get_text(strip=True)
        if text.isdigit():
            num = int(text)
            if 1 <= num <= 99:  # Valid jersey number range
                return str(num)
    return ""

def extract_player_info(row):
    """Extract player name, URL, and image from the row"""
    cols = row.find_all('td')
    player_name = ""
    player_url = ""
    player_image = ""
    
    # Look for player link (usually in columns 1-3)
    for i in range(min(4, len(cols))):
        links = cols[i].find_all('a', href=True)
        for link in links:
            href = link.get('href', '')
            if '/profil/spieler/' in href:
                player_name = link.get_text(strip=True)
                player_url = urljoin("https://www.transfermarkt.com", href)
                
                # Look for player image in the same cell
                img = link.find('img')
                if img and img.get('src'):
                    img_src = img.get('src')
                    if img_src.startswith('//'):
                        img_src = 'https:' + img_src
                    elif img_src.startswith('/'):
                        img_src = 'https://img.transfermarkt.com' + img_src
                    
                    # Check if this looks like a player image
                    if ('spieler' in img_src.lower() or 'portrait' in img_src.lower()):
                        player_image = img_src
                
                break
        if player_name:
            break
    
    return player_name, player_url, player_image

def extract_age_simple(row):
    """Extract age directly from the table - look for numbers that could be age"""
    cols = row.find_all('td')
    
    # Age is often shown as plain number or in parentheses
    for col in cols:
        text = col.get_text(strip=True)
        
        # Look for age in parentheses like "(25)"
        age_match = re.search(r'\((\d{1,2})\)', text)
        if age_match:
            age = int(age_match.group(1))
            if 16 <= age <= 45:  # Reasonable age range
                return str(age)
        
        # Look for standalone numbers that could be age (not jersey numbers)
        if text.isdigit():
            num = int(text)
            if 16 <= num <= 45:  # Age range, not jersey number
                return str(num)
    
    return ""

def extract_nationality(row):
    """Extract nationality from flag images"""
    cols = row.find_all('td')
    
    # Look for nationality flags in first few columns
    for i in range(min(5, len(cols))):
        images = cols[i].find_all('img')
        for img in images:
            img_src = img.get('src', '').lower()
            img_title = img.get('title', '').strip()
            img_alt = img.get('alt', '').strip()
            
            # Look for flag images (but not club logos)
            if ('flagge' in img_src or 'flag' in img_src) and 'wappen' not in img_src:
                nationality = img_title or img_alt
                if nationality and len(nationality) > 1:
                    return nationality
    
    return ""

def extract_position(row):
    """Extract position from the table"""
    cols = row.find_all('td')
    
    position_keywords = [
        'goalkeeper', 'keeper', 'gk', 'torwart',
        'centre-back', 'center-back', 'cb', 'innenverteidiger', 'central defender',
        'left-back', 'lb', 'right-back', 'rb', 'full-back', 'außenverteidiger',
        'defensive midfield', 'dm', 'cdm', 'defensives mittelfeld', 'defensive midfielder',
        'central midfield', 'cm', 'mittelfeld', 'central midfielder', 'midfielder',
        'attacking midfield', 'am', 'cam', 'offensives mittelfeld', 'attacking midfielder',
        'left winger', 'lw', 'right winger', 'rw', 'winger', 'left wing', 'right wing',
        'centre-forward', 'center-forward', 'cf', 'striker', 'st', 'stürmer',
        'second striker', 'forward', 'attacker'
    ]
    
    # Check middle columns for position
    for i in range(2, min(len(cols), 8)):
        text = cols[i].get_text(strip=True).lower()
        for keyword in position_keywords:
            if keyword in text:
                # Return the original case
                return cols[i].get_text(strip=True)
    
    return ""

def extract_height(row):
    """Extract height information"""
    cols = row.find_all('td')
    
    height_patterns = [
        r'(\d{1}\.\d{2})\s*m',      # 1.85m
        r'(\d{3})\s*cm',            # 185cm
        r"(\d{1}'\d{1,2}\")"        # 6'1"
    ]
    
    for col in cols:
        text = col.get_text(strip=True)
        for pattern in height_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
    
    return ""

def extract_club_info(row):
    """Extract current club information"""
    cols = row.find_all('td')
    
    club_info = {
        'name': '',
        'url': '',
        'logo': '',
        'country': ''
    }
    
    # Look for club info in columns 4-8
    for i in range(4, min(len(cols), 9)):
        col = cols[i]
        
        # Look for club link
        links = col.find_all('a', href=True)
        for link in links:
            href = link.get('href', '')
            text = link.get_text(strip=True)
            
            if '/verein/' in href and text and len(text) > 1:
                club_info['name'] = text
                club_info['url'] = urljoin("https://www.transfermarkt.com", href)
                break
        
        # Look for club logo and country flag
        images = col.find_all('img')
        for img in images:
            img_src = img.get('src', '').lower()
            img_title = img.get('title', '').strip()
            img_alt = img.get('alt', '').strip()
            
            # Club logo
            if 'wappen' in img_src or 'vereinslogo' in img_src:
                if img.get('src'):
                    logo_src = img.get('src')
                    if logo_src.startswith('//'):
                        logo_src = 'https:' + logo_src
                    elif logo_src.startswith('/'):
                        logo_src = 'https://img.transfermarkt.com' + logo_src
                    club_info['logo'] = logo_src
                
                # If no club name yet, try to get it from logo alt/title
                if not club_info['name'] and (img_title or img_alt):
                    club_info['name'] = img_title or img_alt
            
            # Country flag (comes after club logo usually)
            elif club_info['name'] and ('flagge' in img_src or 'flag' in img_src):
                if img_title and len(img_title) > 1:
                    # Make sure it's a country, not a club or player
                    common_countries = [
                        'tunisia', 'algeria', 'morocco', 'egypt', 'france', 'spain', 'italy',
                        'germany', 'england', 'saudi arabia', 'qatar', 'uae', 'kuwait',
                        'brazil', 'argentina', 'senegal', 'nigeria', 'cameroon', 'mali'
                    ]
                    if any(country in img_title.lower() for country in common_countries):
                        club_info['country'] = img_title
                        break
    
    # If no club found
    if not club_info['name']:
        club_info['name'] = "Without Club"
    
    return club_info

def extract_market_value(row):
    """Extract market value"""
    cols = row.find_all('td')
    
    # Market value usually in last few columns
    for i in range(len(cols)-3, len(cols)):
        if i >= 0:
            text = cols[i].get_text(strip=True)
            if '€' in text and any(c.isdigit() for c in text):
                return text
    
    return ""

def fetch_players_for_year(session, year, debug=False):
    """Fetch players for a specific year with simpler extraction"""
    url = f"https://www.transfermarkt.com/esperance-tunis/kader/verein/{club_id}/saison_id/{year}"
    
    try:
        if debug:
            print(f"  Fetching {year}/{year+1}...")
        
        # Random delay
        time.sleep(random.uniform(3.0, 5.0))
        
        response = session.get(url, timeout=30)
        
        if response.status_code == 403:
            print(f"  Got 403 for {year}, trying alternative approach...")
            # Try different user agent
            alt_headers = HEADERS.copy()
            alt_headers["User-Agent"] = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
            response = session.get(url, headers=alt_headers, timeout=30)
        
        if response.status_code != 200:
            print(f"  HTTP {response.status_code} for {year}")
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the squad table
        table = soup.select_one('table.items')
        if not table:
            print(f"  No squad table found for {year}")
            return []
        
        players = []
        rows = table.find_all('tr')[1:]  # Skip header row
        
        for row in rows:
            cols = row.find_all('td')
            if len(cols) < 4:
                continue
            
            # Extract player basic info
            player_name, player_url, player_image = extract_player_info(row)
            if not player_name:
                continue
            
            # Extract all other data
            jersey_number = extract_jersey_number(row)
            age = extract_age_simple(row)
            height = extract_height(row)
            position = extract_position(row)
            nationality = extract_nationality(row)
            club_info = extract_club_info(row)
            market_value = extract_market_value(row)
            
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
                'Current_Club': club_info['name'],
                'Current_Club_URL': club_info['url'],
                'Current_Club_Logo': club_info['logo'],
                'Current_Club_Country': club_info['country'],
                'Market_Value': market_value,
                'Year': year
            }
            
            players.append(player_data)
            
            if debug:
                print(f"    {player_name}: Jersey #{jersey_number}, Age {age}, {nationality}, {club_info['name']}")
        
        print(f"  Added {len(players)} players from {year}/{year+1}")
        return players
        
    except Exception as e:
        print(f"  Error for {year}: {e}")
        return []

def remove_duplicates(all_players):
    """Remove duplicate players, keeping most recent"""
    print(f"\nRemoving duplicates from {len(all_players)} records...")
    
    player_dict = {}
    
    for player in all_players:
        url = player.get('Profile_URL', '')
        name = player.get('Player', '')
        key = url if url else f"name_{name}"
        
        if key not in player_dict:
            player_dict[key] = []
        player_dict[key].append(player)
    
    unique_players = []
    duplicates_found = 0
    
    for key, group in player_dict.items():
        if len(group) == 1:
            unique_players.append(group[0])
        else:
            # Keep most recent
            most_recent = max(group, key=lambda x: x['Year'])
            unique_players.append(most_recent)
            duplicates_found += len(group) - 1
            
            name = group[0]['Player']
            seasons = [p['Season'] for p in group]
            print(f"  {name}: {len(seasons)} seasons, keeping {most_recent['Season']}")
    
    # Clean up
    for player in unique_players:
        if 'Year' in player:
            del player['Year']
    
    print(f"Removed {duplicates_found} duplicates, {len(unique_players)} unique players remain")
    return unique_players

def filter_retired_players(players):
    """Remove retired players"""
    active_players = []
    retired_count = 0
    
    for player in players:
        # Simple retirement check
        if player.get('Current_Club', '').lower() in ['retired', 'career ended']:
            retired_count += 1
        else:
            active_players.append(player)
    
    if retired_count > 0:
        print(f"Filtered out {retired_count} retired players")
    
    return active_players

def main():
    """Main scraping function"""
    print(f"Starting Esperance Tunis player scraper")
    print(f"Scraping seasons {start_year}-{current_year}")
    print("=" * 50)
    
    session = create_session()
    all_players = []
    successful_seasons = 0
    
    for i, year in enumerate(years_to_scrape, 1):
        print(f"\nSeason {i}/{len(years_to_scrape)}: {year}/{year+1}")
        
        players = fetch_players_for_year(session, year, debug=False)
        
        if players:
            all_players.extend(players)
            successful_seasons += 1
        
        # Delay between requests
        if i < len(years_to_scrape):
            delay = random.uniform(4.0, 7.0)
            print(f"  Waiting {delay:.1f}s...")
            time.sleep(delay)
    
    print(f"\nScraping complete:")
    print(f"  Successful seasons: {successful_seasons}/{len(years_to_scrape)}")
    print(f"  Total records: {len(all_players)}")
    
    if all_players:
        # Process data
        unique_players = remove_duplicates(all_players)
        active_players = filter_retired_players(unique_players)
        
        # Save to CSV
        filename = f'esperance_players_clean_{start_year}_{current_year}.csv'
        fieldnames = [
            'Player', 'Season', 'Jersey_Number', 'Age', 'Height', 'Position', 
            'Nationality', 'Player_Image', 'Profile_URL', 'Current_Club', 
            'Current_Club_URL', 'Current_Club_Logo', 'Current_Club_Country', 'Market_Value'
        ]
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(active_players)
        
        print(f"\nSaved {len(active_players)} players to {filename}")
        
        # Data quality stats
        with_nationality = len([p for p in active_players if p['Nationality']])
        with_age = len([p for p in active_players if p['Age']])
        with_jersey = len([p for p in active_players if p['Jersey_Number']])
        with_images = len([p for p in active_players if p['Player_Image']])
        with_club_country = len([p for p in active_players if p['Current_Club_Country']])
        
        print(f"\nData Quality:")
        print(f"  Total players: {len(active_players)}")
        print(f"  With nationality: {with_nationality} ({with_nationality/len(active_players)*100:.1f}%)")
        print(f"  With age: {with_age} ({with_age/len(active_players)*100:.1f}%)")
        print(f"  With jersey numbers: {with_jersey} ({with_jersey/len(active_players)*100:.1f}%)")
        print(f"  With images: {with_images} ({with_images/len(active_players)*100:.1f}%)")
        print(f"  With club country: {with_club_country} ({with_club_country/len(active_players)*100:.1f}%)")
        
        # Show samples
        print(f"\nSample players:")
        for i, player in enumerate(active_players[:5], 1):
            print(f"  {i}. {player['Player']} ({player['Season']})")
            print(f"     #{player['Jersey_Number']} | Age: {player['Age']} | {player['Nationality']}")
            print(f"     {player['Position']} | {player['Current_Club']} ({player['Current_Club_Country']})")
    
    else:
        print("No players found!")

if __name__ == "__main__":
    main()