import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import csv
import re
from urllib.parse import urljoin
import json

def get_country_code(country):
    """Map country names to Flashscore country codes"""
    country_mapping = {
        'Tunisia': 'tunisia',
        'Algeria': 'algeria',
        'Libya': 'libya',
        'Egypt': 'egypt',
        'Nigeria': 'nigeria',
        'Ghana': 'ghana',
        'Cote d\'Ivoire': 'cote-d-ivoire',
        'Côte d\'Ivoire': 'cote-d-ivoire',
        'Kuwait': 'kuwait',
        'Iraq': 'iraq',
        'Saudi Arabia': 'saudi-arabia',
        'Brazil': 'brazil'
    }
    return country_mapping.get(country)

def extract_teams_from_matches_and_standings(soup, country):
    """Extract team names and potential URLs from match results and standings"""
    teams_dict = {}
    
    print("Analyzing page structure...")
    
    # Method 1: Look for team names in match results
    print("Looking for teams in match results...")
    
    # Find all text that might contain team names
    all_text_elements = soup.find_all(text=True)
    
    # Common team indicators from your CSV
    known_teams = {
        'Tunisia': ['Esperance', 'ES Sahel', 'CA Bizertin', 'US Monastir', 'JS Kairouan', 'EO Sidi Bouzid', 'AS Soliman', 'US Ben Guerdane'],
        'Libya': ['Asswehly', 'Al-Ahli', 'Al-Ittihad'],
        'Algeria': ['CR Belouizdad', 'USM Alger', 'MC Algiers', 'USM El Harrach'],
        'Nigeria': ['Abia Warriors'],
        'Ghana': ['Al-Jandal'],
        'Cote d\'Ivoire': ['Asswehly', 'Al-Ahly']
    }
    
    # Look for these team names in the page content
    country_teams = known_teams.get(country, [])
    page_content = soup.get_text().lower()
    
    for team in country_teams:
        team_lower = team.lower()
        if team_lower in page_content:
            print(f"Found '{team}' mentioned in page content")
            
            # Try to find a link for this team
            # Look for links that contain the team name or similar
            potential_links = soup.find_all('a', href=True)
            
            for link in potential_links:
                link_text = link.get_text(strip=True).lower()
                href = link.get('href', '')
                
                # Check if this link might be for the team
                if (team_lower in link_text or 
                    any(word in link_text for word in team_lower.split()) or
                    team_lower.replace(' ', '') in link_text.replace(' ', '')):
                    
                    # Build full URL
                    if href.startswith('http'):
                        full_url = href
                    elif href.startswith('/'):
                        full_url = 'https://www.flashscore.com' + href
                    else:
                        continue
                    
                    teams_dict[team_lower] = {
                        'name': team,
                        'url': full_url,
                        'country': country,
                        'source': 'content_match',
                        'confidence': 'high'
                    }
                    print(f"  Found potential link: {full_url}")
                    break
    
    # Method 2: Look for links that might be team pages
    print("Looking for team-like links...")
    
    all_links = soup.find_all('a', href=True)
    for link in all_links:
        href = link.get('href', '')
        link_text = link.get_text(strip=True)
        
        # Skip obviously non-team links
        if any(skip in href.lower() for skip in ['match/', 'player/', 'tournament/', 'league/', 'standings/', 'fixture']):
            continue
            
        # Look for team-like patterns
        if ('/team/' in href or 
            any(team_word in link_text.lower() for team_word in ['fc', 'sc', 'club', 'united', 'city']) or
            any(team.lower() in link_text.lower() for team in country_teams)):
            
            if href.startswith('http'):
                full_url = href
            elif href.startswith('/'):
                full_url = 'https://www.flashscore.com' + href
            else:
                continue
                
            team_key = link_text.lower().strip()
            if team_key and len(team_key) > 1:
                teams_dict[team_key] = {
                    'name': link_text.strip(),
                    'url': full_url,
                    'country': country,
                    'source': 'link_pattern',
                    'confidence': 'medium'
                }
                print(f"  Found team-like link: {link_text} -> {full_url}")
    
    # Method 3: Generate likely URLs based on known team names
    print("Generating likely URLs for known teams...")
    
    for team in country_teams:
        team_lower = team.lower()
        if team_lower not in teams_dict:
            # Generate potential URLs
            team_slug = re.sub(r'[^a-z0-9\s-]', '', team_lower)
            team_slug = re.sub(r'\s+', '-', team_slug)
            team_slug = re.sub(r'-+', '-', team_slug).strip('-')
            
            potential_urls = [
                f"https://www.flashscore.com/team/{team_slug}/",
                f"https://www.flashscore.com/team/{team_slug}-fc/",
                f"https://www.flashscore.com/team/{team_slug}-sc/",
            ]
            
            # Use the first potential URL
            teams_dict[team_lower] = {
                'name': team,
                'url': potential_urls[0],
                'country': country,
                'source': 'generated',
                'confidence': 'low'
            }
            print(f"  Generated URL for {team}: {potential_urls[0]}")
    
    return teams_dict

def scrape_teams_from_country_page(country):
    """Scrape teams from country's Flashscore page with improved targeting"""
    country_code = get_country_code(country)
    if not country_code:
        print(f"Country {country} not mapped to Flashscore")
        return {}
    
    country_url = f"https://www.flashscore.com/football/{country_code}/"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    try:
        print(f"Scraping teams from: {country_url}")
        session = requests.Session()
        response = session.get(country_url, headers=headers, timeout=20)
        
        if response.status_code != 200:
            print(f"Failed to access {country_url}, status code: {response.status_code}")
            return {}
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract teams using improved methods
        teams_dict = extract_teams_from_matches_and_standings(soup, country)
        
        print(f"Found {len(teams_dict)} potential teams for {country}")
        
        # Print results
        if teams_dict:
            print("Teams found:")
            for key, info in teams_dict.items():
                print(f"  - {info['name']}: {info['url']} (source: {info['source']}, confidence: {info['confidence']})")
        
        return teams_dict
        
    except Exception as e:
        print(f"Error scraping {country_url}: {e}")
        return {}

def find_team_link(team_name, teams_dict):
    """Find the best matching team link from scraped data"""
    team_lower = team_name.lower().strip()
    
    # Direct match
    if team_lower in teams_dict:
        match_info = teams_dict[team_lower]
        return match_info['url'], f"Direct match ({match_info['confidence']}, {match_info['source']})"
    
    # Partial match with scoring
    best_match = None
    best_score = 0
    
    for key, info in teams_dict.items():
        score = 0
        
        # Exact word matches get highest score
        team_words = set(team_lower.split())
        key_words = set(key.split())
        exact_matches = team_words & key_words
        if exact_matches:
            score += len(exact_matches) * 0.5
        
        # Substring matches
        if team_lower in key or key in team_lower:
            score += 0.3
        
        # Remove common words and check
        team_clean = team_lower.replace('fc', '').replace('sc', '').replace('club', '').strip()
        key_clean = key.replace('fc', '').replace('sc', '').replace('club', '').strip()
        
        if team_clean in key_clean or key_clean in team_clean:
            score += 0.4
        
        # Boost score based on confidence
        if info['confidence'] == 'high':
            score *= 1.5
        elif info['confidence'] == 'medium':
            score *= 1.2
        
        if score > best_score and score > 0.3:  # Minimum threshold
            best_score = score
            best_match = (info['url'], f'Match score: {score:.2f} ({info["confidence"]}, {info["source"]})')
    
    return best_match if best_match else (None, 'Not found')

def read_csv_and_extract_teams(filename):
    """Read CSV file and extract unique teams with their correct countries"""
    try:
        df = pd.read_csv(filename)
        
        # Find relevant columns
        current_club_col = None
        nationality_col = None
        club_country_col = None
        
        for col in df.columns:
            col_lower = col.lower().strip()
            if 'current_club' in col_lower and not 'country' in col_lower and not 'url' in col_lower and not 'logo' in col_lower:
                current_club_col = col
            elif 'nationality' in col_lower:
                nationality_col = col
            elif 'current_club_country' in col_lower:
                club_country_col = col
        
        if not current_club_col or not nationality_col:
            raise ValueError("Could not find required columns")
        
        print(f"Using columns: {current_club_col}, {nationality_col}, {club_country_col}")
        
        # Extract teams with correct country assignment
        teams_by_country = {}
        
        for _, row in df.iterrows():
            club_name = str(row[current_club_col]).strip()
            nationality = str(row[nationality_col]).strip()
            club_country = str(row[club_country_col]).strip() if club_country_col else ''
            
            # Filter out invalid entries
            if (club_name and 
                club_name not in ['Without Club', 'Tunisia', 'Nigeria', 'nan', ''] and
                nationality and nationality != 'nan'):
                
                # Use club_country if available and valid, otherwise use nationality
                # But group teams by the country where they actually play
                if club_country and club_country != 'nan' and club_country != '':
                    target_country = club_country
                else:
                    target_country = nationality
                
                # Special handling: some teams are listed with wrong countries in CSV
                # Map teams to their actual leagues based on team names
                if club_name in ['Asswehly', 'Al-Ahli'] and 'libya' in club_name.lower():
                    target_country = 'Libya'
                elif club_name in ['CR Belouizdad', 'USM Alger', 'MC Algiers', 'USM El Harrach'] and nationality == 'Algeria':
                    target_country = 'Algeria'
                elif club_name in ['Esperance', 'ES Sahel', 'CA Bizertin', 'US Monastir'] and nationality == 'Tunisia':
                    target_country = 'Tunisia'
                
                if target_country not in teams_by_country:
                    teams_by_country[target_country] = set()
                teams_by_country[target_country].add(club_name)
        
        # Convert to list format
        all_teams = []
        for country, teams in teams_by_country.items():
            for team in teams:
                all_teams.append((team, country))
        
        return all_teams, teams_by_country
    
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return [], {}

def main():
    """Main function"""
    filename = 'esperance_tunis_enhanced_2019.csv'
    
    print("Reading CSV file and extracting teams...")
    teams, teams_by_country = read_csv_and_extract_teams(filename)
    
    if not teams:
        print("No teams found or error reading file.")
        return
    
    print(f"Found {len(teams)} unique teams across {len(teams_by_country)} countries")
    
    # Print summary by country
    for country, team_set in teams_by_country.items():
        print(f"  {country}: {list(team_set)}")
    
    print("\n" + "="*60)
    print("Starting targeted scraping for team links...")
    print("="*60)
    
    # Scrape teams from each country
    all_scraped_teams = {}
    
    for country in teams_by_country.keys():
        print(f"\n--- Processing {country} ---")
        scraped_teams = scrape_teams_from_country_page(country)
        
        # Add country prefix to avoid conflicts
        for key, info in scraped_teams.items():
            all_scraped_teams[f"{country}_{key}"] = info
        
        time.sleep(2)  # Be respectful
    
    print(f"\nTotal teams found: {len(all_scraped_teams)}")
    
    # Match teams from CSV with scraped data
    results = []
    
    print("\n" + "="*60)
    print("Matching CSV teams with scraped data...")
    print("="*60)
    
    for team_name, country in teams:
        print(f"\nLooking for: {team_name} ({country})")
        
        # Look in country-specific scraped data
        country_specific_teams = {
            k.replace(f"{country}_", ""): v 
            for k, v in all_scraped_teams.items() 
            if k.startswith(f"{country}_")
        }
        
        if country_specific_teams:
            url, status = find_team_link(team_name, country_specific_teams)
        else:
            url, status = None, f"No {country} teams scraped"
        
        results.append({
            'Team Name': team_name,
            'Country': country,
            'Flashscore URL': url if url else 'Not Found',
            'Status': status,
            'Country URL': f"https://www.flashscore.com/football/{get_country_code(country)}/" if get_country_code(country) else "N/A"
        })
        
        print(f"Result: {status}")
        if url and url != 'Not Found':
            print(f"URL: {url}")
    
    # Save results
    output_filename = 'flashscore_team_links_final.csv'
    
    with open(output_filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['Team Name', 'Country', 'Flashscore URL', 'Status', 'Country URL']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for result in results:
            writer.writerow(result)
    
    print(f"\n" + "="*60)
    print("FINAL SUMMARY")
    print("="*60)
    print(f"Results saved to: {output_filename}")
    
    # Calculate success metrics
    found_count = sum(1 for r in results if r['Flashscore URL'] != 'Not Found')
    success_rate = (found_count / len(results) * 100) if results else 0
    
    print(f"\nResults Summary:")
    print(f"Total teams processed: {len(results)}")
    print(f"Teams with URLs found: {found_count}")
    print(f"Success rate: {success_rate:.1f}%")
    
    # Show found teams
    if found_count > 0:
        print(f"\nTeams with URLs found:")
        for result in results:
            if result['Flashscore URL'] != 'Not Found':
                print(f"✓ {result['Team Name']} ({result['Country']})")
                print(f"  {result['Flashscore URL']}")

if __name__ == "__main__":
    main()