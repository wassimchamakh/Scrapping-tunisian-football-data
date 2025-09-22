import requests
from bs4 import BeautifulSoup
import csv
import time
import random
from urllib.parse import urljoin
from datetime import datetime
import re
import json
import os
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configuration
club_id = 3342
test_year = 2019
current_year = datetime.now().year

# Enhanced User Agents - more diverse and recent
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0"
]

# Proxy rotation (add your own proxy list if available)
PROXY_LIST = [
    # Add your proxy servers here if you have them
    # {'http': 'http://proxy1:port', 'https': 'http://proxy1:port'},
    # {'http': 'http://proxy2:port', 'https': 'http://proxy2:port'},
]

class SmartSession:
    """Session with enhanced anti-detection features"""
    
    def __init__(self):
        self.session = requests.Session()
        self.setup_session()
        self.request_count = 0
        self.last_request_time = 0
        
    def setup_session(self):
        """Configure session with retry strategy and connection pooling"""
        retry_strategy = Retry(
            total=3,
            status_forcelist=[403, 429, 500, 502, 503, 504],
            backoff_factor=2,
            respect_retry_after_header=True
        )
        
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=20
        )
        
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set common session headers
        self.session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,de;q=0.8,fr;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
    
    def get_dynamic_headers(self):
        """Generate realistic, varied headers for each request"""
        user_agent = random.choice(USER_AGENTS)
        
        headers = {
            'User-Agent': user_agent,
            'Cache-Control': random.choice(['no-cache', 'max-age=0', 'no-store']),
            'Pragma': random.choice(['no-cache', '']),
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': random.choice(['"Windows"', '"macOS"', '"Linux"']),
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': random.choice(['none', 'same-origin', 'cross-site']),
            'sec-fetch-user': '?1'
        }
        
        # Add Chrome-specific headers for Chrome user agents
        if 'Chrome' in user_agent:
            headers['sec-ch-ua'] = '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"'
        
        # Random additional headers
        if random.random() > 0.5:
            headers['X-Requested-With'] = 'XMLHttpRequest'
        
        return headers
    
    def smart_delay(self):
        """Intelligent delay between requests"""
        self.request_count += 1
        current_time = time.time()
        
        # Base delay increases with request count
        base_delay = min(3 + (self.request_count // 10) * 0.5, 8)
        
        # Add randomization
        delay = base_delay + random.uniform(0.5, 2.0)
        
        # Ensure minimum time between requests
        time_since_last = current_time - self.last_request_time
        if time_since_last < delay:
            additional_wait = delay - time_since_last
            time.sleep(additional_wait)
        
        self.last_request_time = time.time()
    
    def make_request(self, url, max_retries=4):
        """Make request with advanced anti-detection"""
        for attempt in range(max_retries):
            try:
                # Smart delay before request
                if attempt > 0:
                    backoff_delay = (2 ** attempt) + random.uniform(1, 3)
                    print(f"        ⏳ Waiting {backoff_delay:.1f}s before retry...")
                    time.sleep(backoff_delay)
                else:
                    self.smart_delay()
                
                # Update headers for this request
                headers = self.get_dynamic_headers()
                
                # Use proxy if available
                proxies = None
                if PROXY_LIST and random.random() > 0.7:  # Use proxy 30% of the time
                    proxies = random.choice(PROXY_LIST)
                
                response = self.session.get(
                    url, 
                    headers=headers,
                    proxies=proxies,
                    timeout=20,
                    allow_redirects=True
                )
                
                if response.status_code == 200:
                    return response
                elif response.status_code == 403:
                    print(f"        🚫 HTTP 403 (blocked) - attempt {attempt + 1}/{max_retries}")
                    # Check if it's a temporary block
                    if 'temporarily blocked' in response.text.lower():
                        print("        ⏳ Temporary block detected, longer wait...")
                        time.sleep(random.uniform(15, 30))
                elif response.status_code == 429:
                    print(f"        ⚠️ HTTP 429 (rate limited) - attempt {attempt + 1}/{max_retries}")
                    # Respect rate limiting
                    retry_after = response.headers.get('Retry-After', '60')
                    wait_time = int(retry_after) if retry_after.isdigit() else 60
                    print(f"        ⏳ Rate limited, waiting {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    print(f"        ⚠️ HTTP {response.status_code} - attempt {attempt + 1}/{max_retries}")
                
            except requests.exceptions.Timeout:
                print(f"        ⏰ Timeout - attempt {attempt + 1}/{max_retries}")
            except requests.exceptions.ConnectionError as e:
                print(f"        🔌 Connection error - attempt {attempt + 1}/{max_retries}: {str(e)[:50]}")
            except Exception as e:
                print(f"        ❌ Request error - attempt {attempt + 1}/{max_retries}: {str(e)[:50]}")
        
        return None

# Global session instance
smart_session = SmartSession()

def detect_retirement_status_enhanced(soup, debug=False):
    """Enhanced retirement detection with multiple strategies"""
    if not soup:
        return None
    
    page_text = soup.get_text().lower()
    
    # Strong retirement indicators
    definitive_patterns = [
        r'career\s+(end|ended)[:\s]*(\d{2}\.\d{2}\.\d{4}|\d{4})',
        r'retired[:\s]*(\d{2}\.\d{2}\.\d{4}|\d{4})',
        r'retirement[:\s]*(\d{2}\.\d{2}\.\d{4}|\d{4})',
        r'end\s+of\s+career[:\s]*(\d{2}\.\d{2}\.\d{4}|\d{4})',
        r'spiellaufbahn\s+beendet',  # German
        r'karriere\s+beendet'        # German
    ]
    
    for pattern in definitive_patterns:
        match = re.search(pattern, page_text)
        if match:
            if debug:
                print(f"        🏁 Retirement indicator found: {match.group(0)}")
            return "Retired"
    
    # Check for structured retirement data
    retirement_elements = soup.find_all(
        ['div', 'span', 'td', 'th'], 
        string=re.compile(r'(career\s+end|retired|retirement|karriere\s+beendet)', re.I)
    )
    
    for element in retirement_elements:
        parent_text = element.parent.get_text() if element.parent else element.get_text()
        if re.search(r'\d{4}', parent_text):  # Contains a year
            if debug:
                print(f"        🏁 Retirement found in structured data")
            return "Retired"
    
    # Enhanced without club detection
    without_club_patterns = [
        r'without\s+club\s+since[:\s]*(\d{2}\.\d{2}\.\d{4})',
        r'vereinslos\s+seit[:\s]*(\d{2}\.\d{2}\.\d{4})',
        r'free\s+agent\s+since[:\s]*(\d{2}\.\d{2}\.\d{4})',
        r'last\s+club[:\s]*.*(\d{2}\.\d{2}\.\d{4})'
    ]
    
    for pattern in without_club_patterns:
        match = re.search(pattern, page_text)
        if match:
            date_str = match.group(1)
            try:
                without_since = datetime.strptime(date_str, '%d.%m.%Y')
                years_without = (datetime.now() - without_since).days / 365.25
                
                if years_without > 3:  # More than 3 years without club
                    if debug:
                        print(f"        🏁 Without club for {years_without:.1f} years - likely retired")
                    return "Retired"
                else:
                    if debug:
                        print(f"        ⏳ Without club since {date_str}")
                    return "Without Club"
            except:
                return "Without Club"
    
    # Check for "Without Club" or "Vereinslos" text
    if re.search(r'\b(without\s+club|vereinslos|free\s+agent)\b', page_text):
        if debug:
            print(f"        ⏳ Without club status detected")
        return "Without Club"
    
    return None

def get_enhanced_club_info(player_url, debug=False):
    """Enhanced club detection with multiple fallback strategies"""
    if not player_url:
        return {}, "Unknown"
    
    try:
        if debug:
            print(f"        🔍 Fetching club info: {player_url[:50]}...")
        
        response = smart_session.make_request(player_url)
        if not response:
            return {}, "Access Blocked"
        
        soup = BeautifulSoup(response.text, 'html.parser')
        details = {}
        current_club = ""
        
        # STRATEGY 1: Header/Profile section (highest priority)
        header_selectors = [
            '.data-header__club a[href*="/verein/"]:not([href*="/verein/515"])',
            '.data-header .club-link:not([href*="/verein/515"])',
            '.dataMain .club a[href*="/verein/"]:not([href*="/verein/515"])',
            'h1 + div a[href*="/verein/"]:not([href*="/verein/515"])'
        ]
        
        for selector in header_selectors:
            try:
                club_element = soup.select_one(selector)
                if club_element and club_element.get('href'):
                    club_name = club_element.get_text(strip=True)
                    if club_name and len(club_name) > 1:
                        current_club = club_name
                        details['current_club_url'] = urljoin("https://www.transfermarkt.com", club_element['href'])
                        if debug:
                            print(f"        🏟️ Found current club (header): {current_club}")
                        break
            except:
                continue
        
        # STRATEGY 2: Recent transfer history
        if not current_club:
            transfer_tables = soup.find_all('table', {'class': ['items', 'responsive-table']})
            
            for table in transfer_tables[:3]:
                rows = table.find_all('tr')
                
                for row in rows[:8]:  # Check more rows
                    try:
                        cols = row.find_all(['td', 'th'])
                        
                        # Look for recent dates (2020+)
                        row_text = row.get_text()
                        recent_years = re.findall(r'20(2[0-9]|1[89])', row_text)
                        
                        if recent_years:
                            # Find club links in this row
                            for col in cols:
                                club_links = col.find_all('a', href=lambda x: x and '/verein/' in x)
                                for link in club_links:
                                    href = link.get('href', '')
                                    if 'verein/515' not in href and 'verein/123' not in href:
                                        club_name = link.get_text(strip=True)
                                        if club_name and len(club_name) > 1:
                                            current_club = club_name
                                            details['current_club_url'] = urljoin("https://www.transfermarkt.com", href)
                                            if debug:
                                                print(f"        🏟️ Found club (transfer history): {current_club}")
                                            break
                                if current_club:
                                    break
                            if current_club:
                                break
                    except:
                        continue
                if current_club:
                    break
        
        # STRATEGY 3: Performance/statistics tables
        if not current_club:
            current_seasons = ['24/25', '2024/25', '2024', '2025', '23/24', '2023/24', '22/23', '2022/23', '21/22', '2021/22']
            
            perf_tables = soup.find_all('table')
            for table in perf_tables:
                try:
                    rows = table.find_all('tr')
                    for row in rows[:10]:
                        cols = row.find_all(['td', 'th'])
                        if len(cols) >= 2:
                            season_text = cols[0].get_text(strip=True)
                            
                            if any(season in season_text for season in current_seasons):
                                for col in cols[1:]:
                                    club_links = col.find_all('a', href=lambda x: x and '/verein/' in x)
                                    for link in club_links:
                                        href = link.get('href', '')
                                        if 'verein/515' not in href and 'verein/123' not in href:
                                            club_name = link.get_text(strip=True)
                                            if club_name and len(club_name) > 1:
                                                current_club = club_name
                                                details['current_club_url'] = urljoin("https://www.transfermarkt.com", href)
                                                if debug:
                                                    print(f"        🏟️ Found club (performance): {current_club}")
                                                break
                                    if current_club:
                                        break
                                if current_club:
                                    break
                        if current_club:
                            break
                except:
                    continue
                if current_club:
                    break
        
        # STRATEGY 4: Text analysis and context scoring
        if not current_club:
            all_club_links = soup.find_all('a', href=lambda x: x and '/verein/' in x and '/startseite' in x)
            
            club_scores = {}
            
            for link in all_club_links:
                try:
                    href = link.get('href', '')
                    club_name = link.get_text(strip=True)
                    
                    if ('verein/515' in href or 'verein/123' in href or 
                        not club_name or len(club_name) < 2):
                        continue
                    
                    score = 0
                    
                    # Get surrounding context
                    context = ""
                    for parent in [link.parent, link.parent.parent if link.parent else None]:
                        if parent:
                            context += parent.get_text().lower()
                    
                    # Score based on context keywords
                    recent_keywords = ['current', '2024', '2025', '2023', 'since', 'joined', 'contract', 'plays', 'player']
                    score += sum(3 for keyword in recent_keywords if keyword in context)
                    
                    # Position in page (earlier = more likely current)
                    page_html = str(soup).lower()
                    position = page_html.find(club_name.lower())
                    if position < len(page_html) * 0.2:  # First 20% of page
                        score += 2
                    elif position < len(page_html) * 0.5:  # First 50% of page
                        score += 1
                    
                    # Frequency bonus
                    frequency = page_html.count(club_name.lower())
                    if frequency > 3:
                        score += 2
                    elif frequency > 1:
                        score += 1
                    
                    if score > 0:
                        club_scores[club_name] = {'score': score, 'url': href}
                
                except:
                    continue
            
            # Pick the highest scoring club
            if club_scores:
                best_club = max(club_scores.items(), key=lambda x: x[1]['score'])
                if best_club[1]['score'] > 2:  # Minimum confidence threshold
                    current_club = best_club[0]
                    details['current_club_url'] = urljoin("https://www.transfermarkt.com", best_club[1]['url'])
                    if debug:
                        print(f"        🏟️ Found club (context analysis, score {best_club[1]['score']}): {current_club}")
        
        # STRATEGY 5: Check for retirement/without club status
        if not current_club:
            retirement_status = detect_retirement_status_enhanced(soup, debug)
            if retirement_status:
                if retirement_status == "Retired":
                    details['current_club_url'] = "https://www.transfermarkt.com/retired/startseite/verein/123"
                    return details, "Retired"
                elif retirement_status == "Without Club":
                    details['current_club_url'] = "https://www.transfermarkt.com/vereinslos/startseite/verein/515"
                    return details, "Without Club"
        
        # If no club found, mark as unknown
        if not current_club:
            if debug:
                print(f"        ❓ No current club information found")
            return details, "Unknown"
        
        # Get additional club information
        if current_club not in ["Retired", "Without Club", "Unknown", "Access Blocked"]:
            # Extract club logo
            logo_selectors = [
                '.data-header__club img',
                'img[src*="wappen"]',
                'img[data-src*="wappen"]',
                'img[src*="vereinslogo"]'
            ]
            
            for selector in logo_selectors:
                try:
                    logo_img = soup.select_one(selector)
                    if logo_img:
                        logo_src = logo_img.get('src') or logo_img.get('data-src')
                        if logo_src and 'wappen' in logo_src.lower():
                            details['current_club_logo'] = urljoin("https://www.transfermarkt.com", logo_src)
                            if debug:
                                print(f"        🎨 Club logo found")
                            break
                except:
                    continue
            
            # Get club country information with controlled requests
            if details.get('current_club_url') and random.random() > 0.3:  # Only fetch club page 70% of the time
                try:
                    club_response = smart_session.make_request(details['current_club_url'])
                    if club_response:
                        club_soup = BeautifulSoup(club_response.text, 'html.parser')
                        
                        # Look for country information
                        flag_selectors = [
                            'img[src*="flagge"]',
                            'img[data-src*="flagge"]',
                            'img[title][src*="flag"]'
                        ]
                        
                        for selector in flag_selectors:
                            try:
                                flag_img = club_soup.select_one(selector)
                                if flag_img:
                                    country = flag_img.get('title', '').strip()
                                    if country and len(country) > 1:
                                        # Filter out non-country titles
                                        invalid_titles = ['logo', 'wappen', 'crest', 'badge', 'icon']
                                        if not any(word in country.lower() for word in invalid_titles):
                                            details['current_club_country'] = country
                                            if debug:
                                                print(f"        🌍 Club country: {country}")
                                            break
                            except:
                                continue
                except Exception as e:
                    if debug:
                        print(f"        ⚠️ Could not fetch club country: {str(e)[:30]}")
        
        return details, current_club
        
    except Exception as e:
        if debug:
            print(f"        ❌ Error in enhanced club info: {str(e)[:50]}")
        return {}, "Error"

def get_enhanced_player_details(player_url, debug=False):
    """Enhanced player details extraction"""
    if not player_url:
        return {}
    
    try:
        response = smart_session.make_request(player_url)
        if not response:
            return {}
        
        soup = BeautifulSoup(response.text, 'html.parser')
        details = {}
        
        # Extract height with multiple patterns
        height_patterns = [
            r'height[:\s]*(\d+[,\.]\d+\s*m)',
            r'size[:\s]*(\d+[,\.]\d+\s*m)',
            r'körpergröße[:\s]*(\d+[,\.]\d+\s*m)',
            r'größe[:\s]*(\d+[,\.]\d+\s*m)',
            r'(\d+[,\.]\d+)\s*m(?:\s|$)'
        ]
        
        page_text = soup.get_text()
        for pattern in height_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                height_value = match.group(1).replace(',', '.')
                # Validate height is reasonable (1.50m - 2.20m)
                try:
                    height_float = float(height_value)
                    if 1.5 <= height_float <= 2.2:
                        details['height'] = f"{height_value} m"
                        if debug:
                            print(f"        📏 Height: {details['height']}")
                        break
                except:
                    continue
        
        # Extract player image with better selectors
        img_selectors = [
            'img[data-src*="portrait/header"]',
            'img[src*="portrait/header"]',
            'img[data-src*="portrait/medium"]',
            'img[src*="portrait/medium"]',
            '.dataBild img',
            '.dataImage img'
        ]
        
        for selector in img_selectors:
            try:
                img = soup.select_one(selector)
                if img:
                    img_src = img.get('data-src') or img.get('src')
                    if (img_src and 'data:image' not in img_src and 
                        'default' not in img_src.lower() and
                        'portrait' in img_src):
                        details['player_image'] = urljoin("https://www.transfermarkt.com", img_src)
                        if debug:
                            print(f"        📸 Player image found")
                        break
            except:
                continue
        
        return details
        
    except Exception as e:
        if debug:
            print(f"        ❌ Error in player details: {str(e)[:50]}")
        return {}

# Keep existing extraction functions (they work well)
def extract_jersey_number(cols):
    for col in cols[:5]:
        col_text = col.get_text(strip=True)
        if col_text.isdigit() and 1 <= int(col_text) <= 99:
            return col_text
    return ""

def extract_age_from_table(cols):
    for col in cols[1:8]:
        col_text = col.get_text(strip=True)
        age_match = re.search(r'\b(\d{2})\b', col_text)
        if age_match:
            age = int(age_match.group(1))
            if 15 <= age <= 45:
                return str(age)
    return ""

def extract_nationality_from_table(cols):
    for col in cols:
        flag_imgs = col.find_all('img', src=lambda x: x and ('flagge' in x.lower() or 'flag' in x.lower()))
        for img in flag_imgs:
            title = img.get('title', '').strip()
            if title and len(title) > 1 and not title.isdigit():
                return title
    return ""

def extract_position_from_table(cols):
    position_map = {
        'torwart': 'Goalkeeper', 'goalkeeper': 'Goalkeeper', 'tw': 'Goalkeeper',
        'innenverteidiger': 'Centre-Back', 'centre-back': 'Centre-Back', 'cb': 'Centre-Back',
        'linksverteidiger': 'Left-Back', 'left-back': 'Left-Back', 'lb': 'Left-Back',
        'rechtsverteidiger': 'Right-Back', 'right-back': 'Right-Back', 'rb': 'Right-Back',
        'defensives mittelfeld': 'Defensive Midfield', 'dm': 'Defensive Midfield',
        'zentrales mittelfeld': 'Central Midfield', 'cm': 'Central Midfield',
        'offensives mittelfeld': 'Attacking Midfield', 'am': 'Attacking Midfield',
        'linksaußen': 'Left Winger', 'left winger': 'Left Winger', 'lw': 'Left Winger',
        'rechtsaußen': 'Right Winger', 'right winger': 'Right Winger', 'rw': 'Right Winger',
        'mittelstürmer': 'Centre-Forward', 'cf': 'Centre-Forward',
        'stürmer': 'Striker', 'striker': 'Striker'
    }
    
    for col in cols[1:8]:
        col_text = col.get_text(strip=True).lower()
        for keyword, position in position_map.items():
            if keyword in col_text:
                return position
    return ""

def extract_market_value_from_table(cols):
    for col in cols:
        val_text = col.get_text(strip=True)
        if '€' in val_text and any(c.isdigit() for c in val_text):
            cleaned = re.sub(r'\s+', ' ', val_text).strip()
            if re.search(r'€\s*[\d,.]+(k|m|th)?', cleaned, re.IGNORECASE):
                return cleaned
    return ""

def fetch_players_enhanced(year, debug=False):
    """Enhanced player fetching with improved blocking resistance"""
    url = f"https://www.transfermarkt.com/esperance-tunis/kader/verein/{club_id}/saison_id/{year}"
    
    try:
        if debug:
            print(f"  🌐 Fetching {year}/{year+1} season: {url}")
        
        response = smart_session.make_request(url)
        if not response:
            print(f"  ❌ Failed to fetch squad page for year {year}")
            return []
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find squad table with multiple selectors
        table_selectors = [
            'table.items',
            '.responsive-table table',
            'table[class*="squad"]',
            'table[class*="kader"]'
        ]
        
        table = None
        for selector in table_selectors:
            table = soup.select_one(selector)
            if table:
                break
        
        if not table:
            print(f"  ❌ No squad table found for year {year}")
            return []

        players = []
        rows = table.find_all('tr')
        
        # Find player rows
        player_rows = []
        for row in rows:
            cols = row.find_all(['td', 'th'])
            if len(cols) >= 3:
                has_player_link = any(col.find('a', href=lambda x: x and '/profil/spieler/' in x) for col in cols)
                if has_player_link:
                    player_rows.append(row)
        
        print(f"  📊 Found {len(player_rows)} player rows")
        
        for row_index, row in enumerate(player_rows, 1):
            cols = row.find_all(['td', 'th'])
            
            # Extract player info
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
                print(f"    👤 Processing player {row_index}/{len(player_rows)}: {player_name}")
            
            player_url = urljoin("https://www.transfermarkt.com", player_link['href']) if player_link else ""
            
            # Extract table data
            jersey_number = extract_jersey_number(cols)
            age = extract_age_from_table(cols)
            position = extract_position_from_table(cols)
            nationality = extract_nationality_from_table(cols)
            market_value = extract_market_value_from_table(cols)
            
            # Get detailed info with enhanced methods
            player_details = get_enhanced_player_details(player_url, debug) if player_url else {}
            club_details, current_club = get_enhanced_club_info(player_url, debug) if player_url else ({}, "Unknown")
            
            # Compile data
            player_data = {
                'Player': player_name,
                'Season': f"{year}/{year+1}",
                'Jersey_Number': jersey_number,
                'Age': age,
                'Height': player_details.get('height', ''),
                'Position': position,
                'Nationality': nationality,
                'Player_Image': player_details.get('player_image', ''),
                'Profile_URL': player_url,
                'Current_Club': current_club,
                'Current_Club_URL': club_details.get('current_club_url', ''),
                'Current_Club_Logo': club_details.get('current_club_logo', ''),
                'Current_Club_Country': club_details.get('current_club_country', ''),
                'Market_Value': market_value
            }
            
            players.append(player_data)
            
            # Status indicator
            if current_club in ["Access Blocked", "Error"]:
                status = "🚫"
            elif current_club in ["Unknown"]:
                status = "❓"
            elif current_club in ["Retired", "Without Club"]:
                status = "⚠️"
            else:
                status = "✅"
            
            if debug:
                print(f"    {status} Player {row_index} completed: {current_club}")
            
            # Progress indicator for long lists
            if row_index % 5 == 0:
                success_rate = len([p for p in players if p['Current_Club'] not in ['Access Blocked', 'Error', 'Unknown']]) / len(players) * 100
                print(f"    📊 Progress: {row_index}/{len(player_rows)} ({success_rate:.1f}% success rate)")
        
        print(f"  ✅ Successfully processed {len(players)} players for {year}/{year+1}")
        return players

    except Exception as e:
        print(f"  ❌ Error fetching year {year}: {e}")
        return []

def save_results_with_backup(players, year):
    """Save results with backup and recovery options"""
    if not players:
        print("❌ No players to save!")
        return None
    
    filename = f'esperance_tunis_enhanced_{year}.csv'
    backup_filename = f'esperance_tunis_enhanced_{year}_backup.csv'
    
    fieldnames = [
        'Player', 'Season', 'Jersey_Number', 'Age', 'Height', 
        'Position', 'Nationality', 'Player_Image', 'Profile_URL',
        'Current_Club', 'Current_Club_URL', 'Current_Club_Logo', 
        'Current_Club_Country', 'Market_Value'
    ]
    
    try:
        # Save main file
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(players)
        
        # Save backup
        with open(backup_filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(players)
        
        # Save JSON backup for easy recovery
        json_filename = f'esperance_tunis_enhanced_{year}.json'
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(players, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Saved to: {filename}")
        print(f"💾 Backup saved to: {backup_filename}")
        print(f"💾 JSON backup saved to: {json_filename}")
        
        return filename
        
    except Exception as e:
        print(f"❌ Error saving files: {e}")
        return None

def analyze_results(players):
    """Comprehensive results analysis"""
    if not players:
        return
    
    print(f"\n📊 COMPREHENSIVE ANALYSIS")
    print("=" * 50)
    
    total = len(players)
    
    # Club status breakdown
    club_counts = {}
    for p in players:
        club = p['Current_Club']
        club_counts[club] = club_counts.get(club, 0) + 1
    
    # Categorize results
    blocked_players = [p for p in players if p['Current_Club'] in ['Access Blocked', 'Error']]
    unknown_players = [p for p in players if p['Current_Club'] == 'Unknown']
    inactive_players = [p for p in players if p['Current_Club'] in ['Retired', 'Without Club']]
    active_players = [p for p in players if p['Current_Club'] not in ['Access Blocked', 'Error', 'Unknown', 'Retired', 'Without Club']]
    
    print(f"🏟️ CURRENT CLUB STATUS:")
    for club, count in sorted(club_counts.items(), key=lambda x: x[1], reverse=True):
        percentage = count/total*100
        if club in ["Access Blocked", "Error"]:
            emoji = "🚫"
        elif club == "Unknown":
            emoji = "❓"
        elif club in ["Retired", "Without Club"]:
            emoji = "⚠️"
        else:
            emoji = "✅"
        print(f"  {emoji} {club}: {count} players ({percentage:.1f}%)")
    
    # Success metrics
    print(f"\n🎯 SUCCESS METRICS:")
    print(f"  ✅ Active clubs found: {len(active_players)}/{total} ({len(active_players)/total*100:.1f}%)")
    print(f"  ⚠️ Retired/Without club: {len(inactive_players)}/{total} ({len(inactive_players)/total*100:.1f}%)")
    print(f"  ❓ Unknown status: {len(unknown_players)}/{total} ({len(unknown_players)/total*100:.1f}%)")
    print(f"  🚫 Blocked/Error: {len(blocked_players)}/{total} ({len(blocked_players)/total*100:.1f}%)")
    
    # Show successful extractions
    if active_players:
        print(f"\n✅ PLAYERS WITH ACTIVE CLUBS ({len(active_players)}):")
        for i, player in enumerate(active_players[:15], 1):
            country = f" ({player['Current_Club_Country']})" if player['Current_Club_Country'] else ""
            logo = " 🎨" if player['Current_Club_Logo'] else ""
            image = " 📸" if player['Player_Image'] else ""
            height = f" ({player['Height']})" if player['Height'] else ""
            print(f"  {i:2d}. {player['Player']}{height} → {player['Current_Club']}{country}{logo}{image}")
        
        if len(active_players) > 15:
            print(f"     ... and {len(active_players) - 15} more")
    
    # Show problematic cases
    if inactive_players:
        print(f"\n⚠️ RETIRED/WITHOUT CLUB PLAYERS ({len(inactive_players)}):")
        for i, player in enumerate(inactive_players[:10], 1):
            print(f"  {i:2d}. {player['Player']} → {player['Current_Club']}")
        if len(inactive_players) > 10:
            print(f"     ... and {len(inactive_players) - 10} more")
    
    if blocked_players:
        print(f"\n🚫 BLOCKED/ERROR PLAYERS ({len(blocked_players)}):")
        for i, player in enumerate(blocked_players[:10], 1):
            print(f"  {i:2d}. {player['Player']} → {player['Current_Club']}")
        if len(blocked_players) > 10:
            print(f"     ... and {len(blocked_players) - 10} more")
    
    # Data completeness analysis
    print(f"\n📈 DATA COMPLETENESS:")
    fields_to_check = ['Height', 'Player_Image', 'Current_Club_Logo', 'Current_Club_Country']
    for field in fields_to_check:
        filled = len([p for p in players if p[field]])
        print(f"  {field}: {filled}/{total} ({filled/total*100:.1f}%)")

def main():
    """Enhanced main function with better error handling"""
    print("🚀 Enhanced Anti-Block Esperance Tunis Player Scraper")
    print(f"📅 Testing with {test_year}/{test_year+1} season")
    print("🔧 Features: Smart delays, rotating headers, retry logic, enhanced detection")
    print("="*80)
    
    # Initialize session
    print("🔄 Initializing smart session...")
    
    try:
        # Fetch players
        players = fetch_players_enhanced(test_year, debug=True)
        
        if players:
            # Save results
            filename = save_results_with_backup(players, test_year)
            
            if filename:
                print(f"\n🎉 SUCCESS! Data extraction completed")
                
                # Analyze results
                analyze_results(players)
                
                # Additional insights
                total_requests = smart_session.request_count
                success_players = [p for p in players if p['Current_Club'] not in ['Access Blocked', 'Error', 'Unknown']]
                
                print(f"\n📊 PERFORMANCE STATS:")
                print(f"  🌐 Total HTTP requests: {total_requests}")
                print(f"  ⚡ Average requests per player: {total_requests/len(players):.1f}")
                print(f"  🎯 Overall success rate: {len(success_players)/len(players)*100:.1f}%")
                print(f"  💾 Data saved to: {filename}")
                
                # Recommendations
                blocked_count = len([p for p in players if p['Current_Club'] in ['Access Blocked', 'Error']])
                if blocked_count > 0:
                    print(f"\n💡 RECOMMENDATIONS:")
                    print(f"  • {blocked_count} players were blocked - consider using proxies")
                    print(f"  • Try running again later with longer delays")
                    print(f"  • Consider processing players in smaller batches")
                
            else:
                print("❌ Failed to save results!")
        else:
            print("❌ No players found or extraction failed!")
            
    except KeyboardInterrupt:
        print(f"\n⏹️ Process interrupted by user")
        print(f"📊 Processed {smart_session.request_count} requests before interruption")
    except Exception as e:
        print(f"❌ Unexpected error in main: {e}")

if __name__ == "__main__":
    main()