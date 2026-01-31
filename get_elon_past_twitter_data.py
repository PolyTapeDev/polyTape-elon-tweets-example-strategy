import requests
import json
import time
import os
from datetime import datetime, timedelta, timezone

def fetch_elon_tweets_past_year():
    # Configuration
    base_url = "https://xtracker.polymarket.com/api/users/elonmusk/posts"
    output_file = "elon_musk_past_tweets.json"
    
    # --- STEP 0: LOAD EXISTING DATA ---
    existing_posts = []
    existing_platform_ids = set()

    if os.path.exists(output_file):
        try:
            with open(output_file, "r", encoding="utf-8") as f:
                existing_posts = json.load(f)
            
            # Create a set of existing IDs for fast lookup
            for p in existing_posts:
                if 'platformId' in p:
                    existing_platform_ids.add(p['platformId'])
                    
            print(f"Loaded {len(existing_posts)} existing posts from {output_file}.")
        except Exception as e:
            print(f"Error loading existing file (starting fresh): {e}")

    # Calculate dates: From 1 year ago until now
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=365)
    
    fetched_posts_batch = []
    
    # Iterate in 30-day chunks
    current_start = start_date
    print(f"--- Starting fetch from {start_date.isoformat()} to {end_date.isoformat()} ---")

    while current_start < end_date:
        # Define chunk end
        current_end = current_start + timedelta(days=30)
        if current_end > end_date:
            current_end = end_date
        
        start_str = current_start.strftime('%Y-%m-%dT%H:%M:%S.000Z')
        end_str = current_end.strftime('%Y-%m-%dT%H:%M:%S.000Z')
        
        params = {
            "startDate": start_str,
            "endDate": end_str
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; Python/3.9; DataFetcher/1.0)",
            "Accept": "application/json"
        }

        try:
            print(f"Fetching: {start_str} -> {end_str}...", end=" ")
            response = requests.get(base_url, params=params, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                posts_batch = data if isinstance(data, list) else data.get('data', [])
                
                count = len(posts_batch)
                fetched_posts_batch.extend(posts_batch)
                print(f"Success. Found {count} posts.")
            else:
                print(f"Failed. Status: {response.status_code}")
                
        except Exception as e:
            print(f"Error: {e}")

        current_start = current_end
        time.sleep(1)

    print(f"\n--- Fetch Complete. Retrieved {len(fetched_posts_batch)} raw posts. ---")

    # --- STEP 1: MERGE (ONLY EXTEND, NO OVERWRITE) ---
    # We add new posts ONLY if their platformId is not already in the file.
    
    newly_added_count = 0
    
    for post in fetched_posts_batch:
        p_id = post.get('platformId')
        
        # Safety check: ensure platformId exists
        if not p_id:
            continue

        # If we DON'T have this ID yet, add it
        if p_id not in existing_platform_ids:
            
            # --- STEP 1.5: ADD LINKS TO NEW POSTS ---
            if 'tweetLink' not in post:
                post['tweetLink'] = f"https://x.com/elonmusk/status/{p_id}"
            
            existing_posts.append(post)
            existing_platform_ids.add(p_id) # Add to set to prevent duplicates within the new batch itself
            newly_added_count += 1

    print(f"Merged data. Added {newly_added_count} new unique tweets. (Total database: {len(existing_posts)})")

    # --- STEP 2: SORTING ---
    # Sort by 'createdAt' in ascending order (Oldest -> Newest)
    # Using a safe get in case createdAt is missing, defaulting to empty string
    existing_posts.sort(key=lambda x: x.get('createdAt', ''))

    # --- STEP 3: SAVE RESULTS ---
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(existing_posts, f, indent=2, ensure_ascii=False)
    
    print(f"Successfully saved to {output_file}")

if __name__ == "__main__":
    fetch_elon_tweets_past_year()