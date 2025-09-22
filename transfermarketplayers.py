import requests
from bs4 import BeautifulSoup
import csv
import time
import random
from urllib.parse import urljoin
from datetime import datetime

# Configuration
club_id = 3342
start_year = 2012
current_year = datetime.now().year
years_to_scrape = list(range(start_year, current_year + 1))

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

def is_player_retired(cols, player_name, debug=False):
    """Check if a player is retired by looking for retirement indicators"""
    retirement_indicators = [
        'retired', 'career end', 'ende der karriere', 'karriereende',
        'without club', 'vereinslos', 'kein verein', 'no club'
    ]
    
    # Check all columns for retirement text
    for col in cols:
        col_text = col.get_text(strip=True).lower()
        
        # Look for explicit retirement indicators
        for indicator in retirement_indicators:
            if indicator in col_text:
                if debug:
                    print(f"     🚫 Retirement indicator found: '{indicator}' in '{col_text[:30]}'")
                return True
        
        # Check for retirement-specific images or icons
        images = col.find_all('img')
        for img in images:
            img_src = img.get('src', '').lower()
            img_title = img.get('title', '').lower()
            img_alt = img.get('alt', '').lower()
            
            if any(indicator in (img_src + img_title + img_alt) for indicator in ['retired', 'career', 'ende']):
                if debug:
                    print(f"     🚫 Retirement image found")
                return True
    
    return False

def extract_current_club(cols, player_name, debug=False):
    """Extract current club using the working method from previous tests"""
    if debug:
        print(f"   🔧 Extracting club for {player_name}")
    
    # First check if player is retired
    if is_player_retired(cols, player_name, debug):
        return "Retired"
    
    # Check columns 4-7 for club information
    for col_index in range(4, min(8, len(cols))):
        col = cols[col_index]
        
        # Look for club links with both patterns
        club_links = col.find_all('a', href=True)
        for link in club_links:
            href = link.get('href', '')
            link_text = link.get_text(strip=True)
            
            if '/verein/' in href or '/startseite/verein/' in href:
                if link_text and link_text != player_name and len(link_text) > 1:
                    if debug:
                        print(f"     ✅ Found club: '{link_text}'")
                    return link_text
        
        # Look for club logos
        images = col.find_all('img')
        for img in images:
            img_src = img.get('src', '')
            img_title = img.get('title', '').strip()
            img_alt = img.get('alt', '').strip()
            
            if ('vereinslogo' in img_src or 'wappen' in img_src or 
                ('logo' in img_src and 'flagge' not in img_src and 'flag' not in img_src)):
                club_name = img_title or img_alt
                if club_name and len(club_name) > 1:
                    if debug:
                        print(f"     ✅ Found club via logo: '{club_name}'")
                    return club_name
    
    return "Without Club"

def extract_position(cols, player_name):
    """Extract player position"""
    position_keywords = [
        'goalkeeper', 'keeper', 'gk',
        'centre-back', 'center-back', 'central defender', 'cb',
        'left-back', 'lb', 'right-back', 'rb', 'full-back', 'fullback',
        'defensive midfield', 'dm', 'cdm', 'defensive midfielder',
        'central midfield', 'cm', 'central midfielder', 'midfielder',
        'attacking midfield', 'am', 'cam', 'attacking midfielder',
        'left winger', 'lw', 'left wing', 'right winger', 'rw', 'right wing',
        'winger', 'wing', 'wide midfielder',
        'centre-forward', 'center-forward', 'cf', 'striker', 'st',
        'forward', 'attacker'
    ]
    
    # Check columns 2-6 for position information
    for col_index in range(2, min(7, len(cols))):
        col_text = cols[col_index].get_text(strip=True).lower()
        
        for keyword in position_keywords:
            if keyword in col_text:
                original_text = cols[col_index].get_text(strip=True)
                # Clean up if it contains player name
                if player_name.lower() in col_text:
                    cleaned = original_text.replace(player_name, '').strip()
                    if cleaned:
                        return cleaned
                return original_text
    
    return ""

def fetch_players_for_year(year, debug=False):
    """Fetch all players for a specific year"""
    url = f"https://www.transfermarkt.com/esperance-tunis/kader/verein/{club_id}/saison_id/{year}"
    
    try:
        if debug:
            print(f"  🌐 Fetching {year}/{year+1} season: {url}")
        
        response = requests.get(url, headers=HEADERS, timeout=20)
        if response.status_code != 200:
            print(f"  ❌ HTTP {response.status_code} for year {year}")
            return []
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the main table
        table = soup.select_one('table.items')
        if not table:
            print(f"  ❌ No table found for year {year}")
            return []

        players = []
        rows = table.find_all('tr')[1:]  # Skip header row
        
        for row in rows:
            cols = row.find_all('td')
            if len(cols) < 4:
                continue

            # Extract player name and URL
            player_link = None
            player_name = ""
            
            # Look for player profile link
            for col in cols[:4]:
                link = col.find('a', href=lambda x: x and '/profil/spieler/' in x)
                if link:
                    player_link = link
                    player_name = link.get_text(strip=True)
                    break
            
            if not player_name:
                continue
                
            player_url = ""
            if player_link and player_link.get('href'):
                player_url = urljoin("https://www.transfermarkt.com", player_link['href'])

            # Extract other information
            position = extract_position(cols, player_name)
            current_club = extract_current_club(cols, player_name, debug=debug)

            # Extract market value
            market_value = ""
            for col in cols:
                val_text = col.get_text(strip=True)
                if '€' in val_text and any(char.isdigit() for char in val_text):
                    market_value = val_text
                    break

            player_data = {
                'Season': f"{year}/{year+1}",
                'Player': player_name,
                'Profile URL': player_url,
                'Position': position,
                'Current Club': current_club,
                'Market Value': market_value,
                'Year': year  # For internal tracking
            }
            
            players.append(player_data)

        if debug:
            print(f"  ✅ Found {len(players)} players for {year}/{year+1}")
        
        return players

    except Exception as e:
        print(f"  ❌ Error fetching year {year}: {e}")
        return []

def remove_duplicates(all_players):
    """Remove duplicate players, keeping the most recent data"""
    print(f"\n🔄 Removing duplicates from {len(all_players)} total records...")
    
    # Group players by their profile URL (unique identifier)
    player_groups = {}
    
    for player in all_players:
        profile_url = player.get('Profile URL', '')
        player_name = player.get('Player', '')
        
        # Use profile URL as primary key, fall back to name if URL is missing
        key = profile_url if profile_url else f"name_{player_name}"
        
        if key not in player_groups:
            player_groups[key] = []
        
        player_groups[key].append(player)
    
    # Keep only the most recent record for each player
    unique_players = []
    
    for key, group in player_groups.items():
        if len(group) == 1:
            # Only appears in one season
            unique_players.append(group[0])
        else:
            # Multiple seasons - keep the most recent
            most_recent = max(group, key=lambda x: x['Year'])
            unique_players.append(most_recent)
            
            # Debug info for duplicates
            player_name = group[0]['Player']
            seasons = [p['Season'] for p in group]
            print(f"  📋 {player_name}: Found in {len(seasons)} seasons {seasons}, keeping {most_recent['Season']}")
    
    # Remove the internal 'Year' field and sort by player name
    for player in unique_players:
        if 'Year' in player:
            del player['Year']
    
    unique_players.sort(key=lambda x: x['Player'])
    
    print(f"✅ After removing duplicates: {len(unique_players)} unique players")
    return unique_players

def filter_retired_players(players):
    """Filter out retired players from the list"""
    print(f"\n🚫 Filtering out retired players...")
    
    active_players = []
    retired_count = 0
    
    for player in players:
        current_club = player.get('Current Club', '')
        
        # Consider a player retired if:
        # 1. Current Club is "Retired"
        # 2. Current Club is "Without Club" and they haven't played recently
        if current_club == "Retired":
            retired_count += 1
            print(f"  🚫 Retired: {player['Player']} (marked as retired)")
        elif current_club == "Without Club":
            # Additional check: if someone is "Without Club" for too long, they might be retired
            # For now, we'll be conservative and keep "Without Club" players
            # You can adjust this logic based on your needs
            active_players.append(player)
        else:
            active_players.append(player)
    
    print(f"✅ Filtered out {retired_count} retired players")
    print(f"✅ Remaining active players: {len(active_players)}")
    
    return active_players

def main():
    """Main function to scrape all years and remove duplicates"""
    print(f"🚀 Starting comprehensive scraper for Esperance Tunis")
    print(f"📅 Years to scrape: {start_year}-{current_year} ({len(years_to_scrape)} seasons)")
    print("=" * 60)
    
    all_players = []
    successful_years = 0
    
    for i, year in enumerate(years_to_scrape, 1):
        print(f"\n📊 Processing season {i}/{len(years_to_scrape)}: {year}/{year+1}")
        
        players = fetch_players_for_year(year, debug=False)
        
        if players:
            all_players.extend(players)
            successful_years += 1
            print(f"  ✅ Added {len(players)} players from {year}/{year+1}")
        else:
            print(f"  ⚠️ No players found for {year}/{year+1}")
        
        # Add delay between requests to be respectful
        if i < len(years_to_scrape):  # Don't sleep after the last request
            sleep_time = random.uniform(1, 3)
            print(f"  ⏳ Waiting {sleep_time:.1f}s before next request...")
            time.sleep(sleep_time)
    
    print(f"\n📈 Data Collection Summary:")
    print(f"  Successful seasons: {successful_years}/{len(years_to_scrape)}")
    print(f"  Total player records: {len(all_players)}")
    
    if all_players:
        # Remove duplicates first
        unique_players = remove_duplicates(all_players)
        
        # Filter out retired players
        active_players = filter_retired_players(unique_players)
        
        # Save to CSV
        filename = f'esperance_tunis_active_{start_year}_{current_year}.csv'
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['Season', 'Player', 'Profile URL', 'Position', 'Current Club', 'Market Value']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(active_players)
        
        print(f"\n🎉 Complete! Saved {len(active_players)} active players to {filename}")
        
        # Final statistics
        clubs = [p['Current Club'] for p in active_players if p['Current Club'] not in ['Without Club', 'Retired']]
        positions = [p['Position'] for p in active_players if p['Position']]
        without_club = [p for p in active_players if p['Current Club'] == 'Without Club']
        
        print(f"\n📊 FINAL STATISTICS:")
        print(f"  📋 Total active players: {len(active_players)}")
        print(f"  🏟️ Players with current clubs: {len(clubs)}")
        print(f"  🔍 Players without club: {len(without_club)}")
        print(f"  ⚽ Players with positions: {len(positions)}")
        print(f"  🏆 Unique clubs represented: {len(set(clubs))}")
        if clubs:
            club_counts = {club: clubs.count(club) for club in set(clubs)}
            most_common = sorted(club_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            print(f"  📍 Most common clubs: {most_common}")
        
        # Show some example players
        print(f"\n🌟 Sample active players (first 5):")
        for player in active_players[:5]:
            print(f"  • {player['Player']} ({player['Season']}) - {player['Position']} - {player['Current Club']}")
        
        if without_club:
            print(f"\n⚠️ Players without club (first 5):")
            for player in without_club[:5]:
                print(f"  • {player['Player']} ({player['Season']}) - {player['Position']}")
        
    else:
        print(f"❌ No players found in any season!")

if __name__ == "__main__":
    main()