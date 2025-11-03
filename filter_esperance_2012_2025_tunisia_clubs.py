import csv

def filter_tunisia_clubs(input_file, output_file):
    """
    Filter the all seasons CSV to only include players whose current club is in Tunisia.
    Excludes players who are 'Retired' or 'Without Club'.
    """
    
    print(f"📂 Reading from: {input_file}")
    print(f"📝 Will write to: {output_file}")
    print()
    
    tunisia_players = []
    total_count = 0
    tunisia_count = 0
    retired_count = 0
    without_club_count = 0
    other_country_count = 0
    
    with open(input_file, 'r', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)
        
        for row in reader:
            total_count += 1
            
            current_club = row.get('Current_Club', '').strip()
            current_club_country = row.get('Current_Club_Country', '').strip()
            
            # Count different categories
            if current_club == 'Retired':
                retired_count += 1
            elif current_club == 'Without Club':
                without_club_count += 1
            elif current_club_country == 'Tunisia':
                tunisia_count += 1
                tunisia_players.append(row)
            else:
                other_country_count += 1
    
    # Write filtered data to new CSV
    if tunisia_players:
        with open(output_file, 'w', newline='', encoding='utf-8') as outfile:
            fieldnames = tunisia_players[0].keys()
            writer = csv.DictWriter(outfile, fieldnames=fieldnames)
            
            writer.writeheader()
            writer.writerows(tunisia_players)
        
        print(f"✅ Successfully created {output_file}")
        print()
    else:
        print("❌ No players found with Current_Club_Country = Tunisia")
        print()
    
    # Print statistics
    print("=" * 60)
    print("📊 STATISTICS")
    print("=" * 60)
    print(f"Total players processed: {total_count}")
    print(f"Players in Tunisia clubs: {tunisia_count} ({tunisia_count/total_count*100:.1f}%)")
    print(f"Retired players: {retired_count} ({retired_count/total_count*100:.1f}%)")
    print(f"Without Club: {without_club_count} ({without_club_count/total_count*100:.1f}%)")
    print(f"Players in other countries: {other_country_count} ({other_country_count/total_count*100:.1f}%)")
    print("=" * 60)
    print()
    
    # Show breakdown by club for Tunisia-based players
    if tunisia_players:
        print("🇹🇳 TUNISIA CLUBS BREAKDOWN")
        print("=" * 60)
        club_counts = {}
        for player in tunisia_players:
            club = player['Current_Club']
            club_counts[club] = club_counts.get(club, 0) + 1
        
        # Sort by count descending
        sorted_clubs = sorted(club_counts.items(), key=lambda x: x[1], reverse=True)
        
        for club, count in sorted_clubs:
            print(f"{club}: {count} player(s)")
        print("=" * 60)

if __name__ == "__main__":
    input_file = "esperance_2012_2025_all_seasons.csv"
    output_file = "esperance_2012_2025_tunisia_clubs.csv"
    
    filter_tunisia_clubs(input_file, output_file)
    
    print("\n✨ Done! Check the output file for Tunisia-based players only.")
