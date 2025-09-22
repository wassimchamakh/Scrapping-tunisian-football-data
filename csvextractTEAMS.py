import pandas as pd
import os

def split_esperance_csv(input_file):
    """
    Split the Esperance Tunis CSV file into 3 separate files:
    1. Players with clubs that have Flashscore links
    2. Players with clubs but no Flashscore links available
    3. Players without clubs
    """
    
    # Read the CSV file
    try:
        df = pd.read_csv(input_file)
        print(f"Successfully loaded {len(df)} rows from {input_file}")
    except Exception as e:
        print(f"Error reading file: {e}")
        return
    
    # Clean the data - strip whitespace from string columns
    for col in df.select_dtypes(include=['object']).columns:
        df[col] = df[col].astype(str).str.strip()
    
    # Replace 'nan' strings with actual NaN values
    df = df.replace('nan', pd.NA)
    
    # Create the three categories
    
    # 1. Players without clubs
    players_without_clubs = df[
        (df['Current Club'].isna()) | 
        (df['Current Club'].str.lower() == 'without club') | 
        (df['Current Club'] == '') | 
        (df['Current Club'].str.lower() == 'nan')
    ].copy()
    
    # 2. Players with clubs that have Flashscore links
    players_with_flashscore = df[
        (df['Current Club'].notna()) & 
        (df['Current Club'].str.lower() != 'without club') & 
        (df['Current Club'] != '') & 
        (df['Current Club'].str.lower() != 'nan') & 
        (df['Flashscore Link'].notna()) & 
        (df['Flashscore Link'] != 'Unavailable') & 
        (df['Flashscore Link'] != '') & 
        (df['Flashscore Link'].str.contains('flashscore.com', na=False))
    ].copy()
    
    # 3. Players with clubs but no Flashscore links
    players_clubs_no_flashscore = df[
        (df['Current Club'].notna()) & 
        (df['Current Club'].str.lower() != 'without club') & 
        (df['Current Club'] != '') & 
        (df['Current Club'].str.lower() != 'nan') & 
        (
            (df['Flashscore Link'].isna()) | 
            (df['Flashscore Link'] == 'Unavailable') | 
            (df['Flashscore Link'] == '') | 
            (~df['Flashscore Link'].str.contains('flashscore.com', na=False))
        )
    ].copy()
    
    # Create output directory if it doesn't exist
    output_dir = "esperance_split_files"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Save the three files
    file1 = os.path.join(output_dir, "players_with_flashscore_links.csv")
    file2 = os.path.join(output_dir, "players_clubs_no_flashscore.csv")
    file3 = os.path.join(output_dir, "players_without_clubs.csv")
    
    # Save files
    players_with_flashscore.to_csv(file1, index=False)
    players_clubs_no_flashscore.to_csv(file2, index=False)
    players_without_clubs.to_csv(file3, index=False)
    
    # Print summary
    print("\n" + "="*60)
    print("SPLIT SUMMARY")
    print("="*60)
    print(f"Original file: {len(df)} players")
    print(f"\n1. Players with clubs that have Flashscore links: {len(players_with_flashscore)}")
    print(f"   Saved to: {file1}")
    
    print(f"\n2. Players with clubs but no Flashscore links: {len(players_clubs_no_flashscore)}")
    print(f"   Saved to: {file2}")
    
    print(f"\n3. Players without clubs: {len(players_without_clubs)}")
    print(f"   Saved to: {file3}")
    
    print(f"\nTotal accounted for: {len(players_with_flashscore) + len(players_clubs_no_flashscore) + len(players_without_clubs)}")
    
    # Show sample data from each category
    print("\n" + "="*60)
    print("SAMPLE DATA FROM EACH CATEGORY")
    print("="*60)
    
    if len(players_with_flashscore) > 0:
        print("\n1. Sample - Players with Flashscore links:")
        print(players_with_flashscore[['Player', 'Current Club', 'Flashscore Link']].head(3).to_string(index=False))
    
    if len(players_clubs_no_flashscore) > 0:
        print("\n2. Sample - Players with clubs but no Flashscore:")
        print(players_clubs_no_flashscore[['Player', 'Current Club', 'Flashscore Link']].head(3).to_string(index=False))
    
    if len(players_without_clubs) > 0:
        print("\n3. Sample - Players without clubs:")
        print(players_without_clubs[['Player', 'Current Club', 'Flashscore Link']].head(3).to_string(index=False))

def main():
    # Specify your input file name
    input_file = "esperance_tunis_active_2012_2025_with_flashscore.csv"
    
    # Check if file exists
    if not os.path.exists(input_file):
        print(f"Error: File '{input_file}' not found.")
        print("Please make sure the CSV file is in the same directory as this script.")
        return
    
    # Split the CSV
    split_esperance_csv(input_file)
    print("\nDone! Check the 'esperance_split_files' folder for the output files.")

if __name__ == "__main__":
    main()