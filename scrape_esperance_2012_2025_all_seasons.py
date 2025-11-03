"""
Transfermarkt Scraper for Esperance de Tunis - Multiple Seasons (2012-2025)
Extracts complete player data including current club information for all seasons
"""

import requests
from bs4 import BeautifulSoup
import csv
import time
import random
from urllib.parse import urljoin
import re
from datetime import datetime
import json

# Configuration
START_YEAR = 2012
CURRENT_YEAR = 2025  # 2025/2026 season
CLUB_ID = 3342
CLUB_NAME = "esperance-tunis"

# Enhanced headers to avoid bot detection
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,fr;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Cache-Control": "max-age=0",
    "Referer": "https://www.transfermarkt.com/"
}

def create_session():
    """Create a session with proper configuration"""
    session = requests.Session()
    session.headers.update(HEADERS)
    session.cookies.update({
        'tm_cookie_consent': 'functional%2Cstatistics%2Cmarketing',
        'oneTrustCookie': 'true'
    })
    return session

def extract_player_image(soup):
    """Extract player image URL from profile page"""
    try:
        # Method 1: Look in data-header__profile-container
        profile_container = soup.find('div', class_='data-header__profile-container')
        if profile_container:
            img = profile_container.find('img', class_='data-header__profile-image')
            if img:
                src = img.get('src') or img.get('data-src') or ''
                if src and 'portrait' in src and len(src) > 30:
                    return src if src.startswith('http') else urljoin("https://www.transfermarkt.com", src)
        
        # Method 2: Direct image search with portrait keyword
        images = soup.find_all('img')
        for img in images:
            src = img.get('src') or img.get('data-src') or ''
            if 'portrait/header' in src or ('spieler' in src and 'portrait' in src):
                if not any(skip in src.lower() for skip in ['flag', 'wappen', 'logo', 'default']):
                    return src if src.startswith('http') else urljoin("https://www.transfermarkt.com", src)
    except Exception as e:
        pass
    
    return ""

def extract_current_club_info(soup):
    """Extract current club information from player profile"""
    try:
        # Method 1: Look for "Current club:" label in info table (MOST RELIABLE)
        info_table = soup.find('div', class_='info-table')
        if info_table:
            # Find all content spans
            content_spans = info_table.find_all('span', class_='info-table__content')
            
            # Look for "Current club:" label
            for i, span in enumerate(content_spans):
                span_text = span.get_text(strip=True).lower()
                if 'current club' in span_text or span_text == 'current club:':
                    # The next span should contain the club information
                    if i + 1 < len(content_spans):
                        club_span = content_spans[i + 1]
                        
                        # Extract club name from the <a> tag with title attribute
                        club_links = club_span.find_all('a', href=lambda x: x and '/verein/' in x)
                        club_name = ''
                        club_url = ''
                        
                        for link in club_links:
                            # Get club name from title or text
                            club_name = link.get('title', '').strip()
                            if not club_name:
                                club_name = link.get_text(strip=True)
                            
                            if club_name and len(club_name) > 1:  # Valid club name found
                                club_url = urljoin("https://www.transfermarkt.com", link.get('href', ''))
                                break
                        
                        # Extract club logo using srcset or src
                        club_logo = ''
                        logo_imgs = club_span.find_all('img')
                        for img in logo_imgs:
                            # Try srcset first (preferred for quality)
                            srcset = img.get('srcset', '')
                            if srcset:
                                # Extract first URL from srcset (format: "url1 1x, url2 2x")
                                club_logo = srcset.split(',')[0].split()[0].strip()
                            
                            # Fallback to src or data-src
                            if not club_logo:
                                club_logo = img.get('src', '') or img.get('data-src', '')
                            
                            if club_logo and 'wappen' in club_logo:  # Verify it's a club logo
                                if not club_logo.startswith('http'):
                                    club_logo = urljoin("https://www.transfermarkt.com", club_logo)
                                break
                        
                        # Extract club country from the data-header section
                        # Look for the league level section which contains the country flag
                        club_country = ''
                        data_header = soup.find('div', class_='data-header__club-info')
                        if data_header:
                            league_level_spans = data_header.find_all('span', class_='data-header__label')
                            for span in league_level_spans:
                                if 'league level' in span.get_text().lower():
                                    # Find the country flag in the content
                                    content_span = span.find('span', class_='data-header__content')
                                    if content_span:
                                        flag_img = content_span.find('img', class_='flaggenrahmen')
                                        if flag_img:
                                            club_country = flag_img.get('title', '').strip() or flag_img.get('alt', '').strip()
                                            break
                        
                        if club_name:
                            return {
                                'Current_Club': club_name,
                                'Current_Club_URL': club_url,
                                'Current_Club_Logo': club_logo,
                                'Current_Club_Country': club_country
                            }
                    
                    # If we found "Current club:" label but no next span, might be retired
                    break
        
        # Check if player is retired or without club by examining specific patterns
        page_text = soup.get_text(" ", strip=True).lower()
        
        # Check for "Retired" status
        retired_indicators = ['retired', 'career end', 'ende der karriere']
        if any(indicator in page_text for indicator in retired_indicators):
            return {
                'Current_Club': 'Retired',
                'Current_Club_URL': '',
                'Current_Club_Logo': '',
                'Current_Club_Country': ''
            }
        
        # Check for "Without Club" status
        without_club_indicators = ['without club', 'vereinslos', 'sans club']
        if any(indicator in page_text for indicator in without_club_indicators):
            return {
                'Current_Club': 'Without Club',
                'Current_Club_URL': '',
                'Current_Club_Logo': '',
                'Current_Club_Country': ''
            }
        
    except Exception as e:
        print(f"      ⚠️ Error extracting club info: {e}")
    
    # Default fallback
    return {
        'Current_Club': 'Without Club',
        'Current_Club_URL': '',
        'Current_Club_Logo': '',
        'Current_Club_Country': ''
    }

def get_player_details(session, player_url, player_name, debug=False):
    """Get detailed information from player profile page"""
    if not player_url:
        return {}
    
    try:
        if debug:
            print(f"      🔍 Fetching details for: {player_name}")
        
        # Add random delay
        time.sleep(random.uniform(0.8, 1.5))
        
        response = session.get(player_url, timeout=20)
        if response.status_code != 200:
            print(f"      ❌ Failed to fetch player page: HTTP {response.status_code}")
            return {}
        
        soup = BeautifulSoup(response.text, 'html.parser')
        details = {}
        
        # Extract Age and Birth Date
        try:
            birth_span = soup.find('span', {'itemprop': 'birthDate'})
            if birth_span:
                birth_text = birth_span.get_text(strip=True)
                # Parse "Jan 15, 2003 (22)" or "15.01.2003 (22)"
                age_match = re.search(r'\((\d{1,2})\)', birth_text)
                if age_match:
                    details['Age'] = age_match.group(1)
                
                # Extract birth date
                date_match = re.search(r'([A-Za-z]{3}\s+\d{1,2},\s+\d{4}|\d{1,2}\.\d{1,2}\.\d{4})', birth_text)
                if date_match:
                    details['Birth'] = date_match.group(1)
        except:
            pass
        
        # Extract Height
        try:
            height_span = soup.find('span', {'itemprop': 'height'})
            if height_span:
                height_text = height_span.get_text(strip=True)
                # Parse "1.85 m" or "185 cm"
                height_match = re.search(r'(\d{1,2}[.,]\d{2})\s*m', height_text)
                if height_match:
                    details['Height'] = height_match.group(1).replace(',', '.') + 'm'
        except:
            pass
        
        # Extract Nationality
        try:
            # Method 1: Look in info-table for "Citizenship:" label
            info_table = soup.find('div', class_='info-table')
            if info_table:
                content_spans = info_table.find_all('span', class_='info-table__content')
                for i, span in enumerate(content_spans):
                    span_text = span.get_text(strip=True).lower()
                    if 'citizenship' in span_text:
                        # Next span should have the nationality
                        if i + 1 < len(content_spans):
                            nat_span = content_spans[i + 1]
                            # Look for flag image
                            flag_img = nat_span.find('img', class_='flaggenrahmen')
                            if flag_img:
                                nationality = flag_img.get('title', '').strip() or flag_img.get('alt', '').strip()
                                if nationality and len(nationality) > 1:
                                    details['Nationality'] = nationality
                                    break
                            # Fallback: get text after flag
                            nat_text = nat_span.get_text(strip=True)
                            if nat_text and len(nat_text) > 1:
                                details['Nationality'] = nat_text
                                break
            
            # Method 2: Look in data-header for citizenship
            if 'Nationality' not in details:
                data_header = soup.find('div', class_='data-header__details')
                if data_header:
                    # Look for spans with flag images
                    flag_imgs = data_header.find_all('img', class_='flaggenrahmen')
                    for flag in flag_imgs:
                        # Make sure it's not a club/league flag
                        parent_text = flag.find_parent(['span', 'div']).get_text().lower() if flag.find_parent(['span', 'div']) else ''
                        if any(keyword in parent_text for keyword in ['citizenship', 'nationality', 'citizen']):
                            nationality = flag.get('title', '').strip() or flag.get('alt', '').strip()
                            if nationality and len(nationality) > 1:
                                details['Nationality'] = nationality
                                break
        except:
            pass
        
        # Extract Player Image
        details['Player_Image'] = extract_player_image(soup)
        
        # Extract current club information
        club_info = extract_current_club_info(soup)
        details.update(club_info)
        
        # Post-process: Check if "club" is actually a country (national team page)
        # This indicates the player is likely retired
        country_names = [
            'Tunisia', 'Algeria', 'Morocco', 'Egypt', 'Libya', 'Ivory Coast', 
            'Cote d\'Ivoire', 'Nigeria', 'Ghana', 'Senegal', 'Cameroon', 
            'South Africa', 'Mali', 'Burkina Faso', 'France', 'Germany', 
            'Spain', 'Italy', 'England', 'Portugal', 'Brazil', 'Argentina'
        ]
        
        if details.get('Current_Club') in country_names:
            # This is a national team page, player is likely retired or without club
            details['Current_Club'] = 'Retired'
            details['Current_Club_URL'] = ''
            details['Current_Club_Logo'] = ''
            details['Current_Club_Country'] = ''
        
        # Clear club details for "Without Club" or "Retired" players
        if details.get('Current_Club') in ['Without Club', 'Retired']:
            details['Current_Club_URL'] = ''
            details['Current_Club_Logo'] = ''
            details['Current_Club_Country'] = ''
        
        if debug:
            print(f"      ✅ Extracted: Age={details.get('Age', 'N/A')}, Height={details.get('Height', 'N/A')}, "
                  f"Nationality={details.get('Nationality', 'N/A')}, Club={details.get('Current_Club', 'N/A')}")
        
        return details
        
    except Exception as e:
        print(f"      ❌ Error getting player details: {e}")
        return {}

def extract_jersey_number(row):
    """Extract jersey number from table row"""
    try:
        # Look in the first few cells for a number
        cells = row.find_all('td')
        for i, cell in enumerate(cells[:3]):
            text = cell.get_text(strip=True)
            if text.isdigit() and 1 <= int(text) <= 99:
                return text
            
            # Check for number in div/span elements
            for elem in cell.find_all(['div', 'span']):
                elem_text = elem.get_text(strip=True)
                if elem_text.isdigit() and 1 <= int(elem_text) <= 99:
                    return elem_text
    except:
        pass
    return ""

def extract_position(row):
    """Extract player position from table row"""
    position_mapping = {
        'torwart': 'Goalkeeper',
        'goalkeeper': 'Goalkeeper',
        'abwehr': 'Defender',
        'innenverteidiger': 'Centre-Back',
        'centre-back': 'Centre-Back',
        'linksverteidiger': 'Left-Back',
        'left-back': 'Left-Back',
        'rechtsverteidiger': 'Right-Back',
        'right-back': 'Right-Back',
        'mittelfeld': 'Midfield',
        'defensives mittelfeld': 'Defensive Midfield',
        'defensive midfield': 'Defensive Midfield',
        'zentrales mittelfeld': 'Central Midfield',
        'central midfield': 'Central Midfield',
        'offensives mittelfeld': 'Attacking Midfield',
        'attacking midfield': 'Attacking Midfield',
        'sturm': 'Forward',
        'mittelstürmer': 'Centre-Forward',
        'centre-forward': 'Centre-Forward',
        'linksaußen': 'Left Winger',
        'left winger': 'Left Winger',
        'rechtsaußen': 'Right Winger',
        'right winger': 'Right Winger'
    }
    
    try:
        # Look in table cells for position text or title attributes
        cells = row.find_all('td')
        for cell in cells:
            # Check text content
            cell_text = cell.get_text(strip=True).lower()
            for key, value in position_mapping.items():
                if key in cell_text:
                    return value
            
            # Check title attributes
            elements_with_title = cell.find_all(attrs={'title': True})
            for elem in elements_with_title:
                title_text = elem.get('title', '').lower()
                for key, value in position_mapping.items():
                    if key in title_text:
                        return value
    except:
        pass
    
    return ""

def extract_market_value(row):
    """Extract market value from table row"""
    try:
        cells = row.find_all('td')
        for cell in cells:
            cell_text = cell.get_text(strip=True)
            # Look for currency symbols and values
            if any(currency in cell_text for currency in ['€', '$', '£']):
                # Clean up and extract value
                value_match = re.search(r'[€$£]\s*([0-9.,]+[kmKM]?)', cell_text)
                if value_match:
                    return value_match.group(0)
            
            # Sometimes value is without currency symbol
            value_match = re.search(r'\b(\d+(?:[.,]\d+)?[kmKM])\b', cell_text)
            if value_match and 'year' not in cell_text.lower() and 'age' not in cell_text.lower():
                return '€' + value_match.group(1)
    except:
        pass
    
    return ""

def scrape_season(session, year, debug=False):
    """Scrape squad data for a specific season"""
    
    squad_url = f"https://www.transfermarkt.com/{CLUB_NAME}/kader/verein/{CLUB_ID}/saison_id/{year}"
    
    print(f"\n{'='*80}")
    print(f"📅 Season {year}/{year+1}")
    print(f"{'='*80}")
    print(f"🌐 URL: {squad_url}")
    
    try:
        # Add delay between seasons
        time.sleep(random.uniform(2.0, 4.0))
        
        response = session.get(squad_url, timeout=30)
        
        if response.status_code != 200:
            print(f"❌ Failed to fetch squad page: HTTP {response.status_code}")
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the squad table
        table = soup.find('table', class_='items')
        if not table:
            print("❌ Could not find squad table")
            return []
        
        players_data = []
        rows = table.find_all('tr', class_=['odd', 'even'])
        
        print(f"✅ Found {len(rows)} players")
        
        for i, row in enumerate(rows, 1):
            try:
                # Extract player name and profile URL
                player_link = row.find('a', href=lambda x: x and '/profil/spieler/' in x)
                if not player_link:
                    continue
                
                player_name = player_link.get_text(strip=True)
                player_url = urljoin("https://www.transfermarkt.com", player_link.get('href', ''))
                
                # Extract basic info from table
                jersey_number = extract_jersey_number(row)
                position = extract_position(row)
                market_value = extract_market_value(row)
                
                # Get detailed player information (only for first 3 players in debug mode)
                player_details = get_player_details(session, player_url, player_name, debug=debug and i <= 3)
                
                # Compile all data
                player_data = {
                    'Player': player_name,
                    'Season': f"{year}/{year+1}",
                    'Jersey_Number': jersey_number,
                    'Age': player_details.get('Age', ''),
                    'Height': player_details.get('Height', ''),
                    'Position': position,
                    'Nationality': player_details.get('Nationality', ''),
                    'Player_Image': player_details.get('Player_Image', ''),
                    'Profile_URL': player_url,
                    'Current_Club': player_details.get('Current_Club', 'Without Club'),
                    'Current_Club_URL': player_details.get('Current_Club_URL', ''),
                    'Current_Club_Logo': player_details.get('Current_Club_Logo', ''),
                    'Current_Club_Country': player_details.get('Current_Club_Country', ''),
                    'Market_Value': market_value
                }
                
                players_data.append(player_data)
                
                # Show progress every 10 players
                if i % 10 == 0:
                    print(f"  Progress: {i}/{len(rows)} players processed...")
                
            except Exception as e:
                print(f"   ❌ Error processing player {i}: {e}")
                continue
        
        print(f"✅ Successfully scraped {len(players_data)} players from {year}/{year+1}")
        return players_data
        
    except Exception as e:
        print(f"❌ Error scraping season {year}: {e}")
        return []

def remove_duplicates(all_players):
    """Remove duplicate players, keeping the most recent data"""
    print(f"\n{'='*80}")
    print(f"🔄 REMOVING DUPLICATES")
    print(f"{'='*80}")
    print(f"Total records before: {len(all_players)}")
    
    # Group players by their profile URL (unique identifier)
    player_groups = {}
    
    for player in all_players:
        profile_url = player.get('Profile_URL', '')
        player_name = player.get('Player', '')
        
        # Use profile URL as primary key, fall back to name if URL is missing
        key = profile_url if profile_url else f"name_{player_name}"
        
        if key not in player_groups:
            player_groups[key] = []
        
        player_groups[key].append(player)
    
    # Keep only the most recent record for each player (highest season year)
    unique_players = []
    
    for key, group in player_groups.items():
        if len(group) == 1:
            unique_players.append(group[0])
        else:
            # Sort by season and keep most recent
            sorted_group = sorted(group, key=lambda x: int(x['Season'].split('/')[0]), reverse=True)
            unique_players.append(sorted_group[0])
    
    # Sort by player name
    unique_players.sort(key=lambda x: x['Player'])
    
    print(f"Total unique players: {len(unique_players)}")
    print(f"Duplicates removed: {len(all_players) - len(unique_players)}")
    
    return unique_players

def save_to_csv(players_data, filename):
    """Save player data to CSV file"""
    if not players_data:
        print("\n❌ No data to save!")
        return
    
    print(f"\n{'='*80}")
    print(f"💾 SAVING DATA")
    print(f"{'='*80}")
    
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            fieldnames = [
                'Player', 'Season', 'Jersey_Number', 'Age', 'Height', 'Position',
                'Nationality', 'Player_Image', 'Profile_URL', 'Current_Club',
                'Current_Club_URL', 'Current_Club_Logo', 'Current_Club_Country',
                'Market_Value'
            ]
            
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(players_data)
        
        print(f"✅ Successfully saved {len(players_data)} players to {filename}")
        
        # Print statistics
        print(f"\n📊 DATA STATISTICS:")
        complete_fields = {
            'Age': len([p for p in players_data if p['Age']]),
            'Height': len([p for p in players_data if p['Height']]),
            'Position': len([p for p in players_data if p['Position']]),
            'Nationality': len([p for p in players_data if p['Nationality']]),
            'Current_Club': len([p for p in players_data if p['Current_Club'] not in ['', 'Without Club']]),
        }
        
        for field, count in complete_fields.items():
            percentage = (count / len(players_data) * 100) if len(players_data) > 0 else 0
            print(f"   {field}: {count}/{len(players_data)} ({percentage:.1f}%)")
        
    except Exception as e:
        print(f"❌ Error saving to CSV: {e}")

def main():
    """Main execution function"""
    print("\n" + "="*80)
    print("🚀 ESPERANCE DE TUNIS MULTI-SEASON SCRAPER")
    print("="*80)
    print(f"📅 Seasons: {START_YEAR}/{START_YEAR+1} to {CURRENT_YEAR}/{CURRENT_YEAR+1}")
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    session = create_session()
    all_players = []
    
    # Scrape each season
    for year in range(START_YEAR, CURRENT_YEAR + 1):
        season_players = scrape_season(session, year, debug=(year == START_YEAR))
        all_players.extend(season_players)
    
    if all_players:
        # Remove duplicates
        unique_players = remove_duplicates(all_players)
        
        # Save to CSV
        filename = f'esperance_{START_YEAR}_{CURRENT_YEAR}_all_seasons.csv'
        save_to_csv(unique_players, filename)
        
        print("\n" + "="*80)
        print("🎉 SCRAPING COMPLETED SUCCESSFULLY!")
        print(f"⏰ Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)
    else:
        print("\n❌ No data was scraped!")

if __name__ == "__main__":
    main()
