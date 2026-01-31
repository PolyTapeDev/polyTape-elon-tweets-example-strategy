import os
import json
import requests
import time
from datetime import datetime, timezone
from dateutil import parser as date_parser
from dotenv import load_dotenv

# ==========================================
# CONFIGURATION
# ==========================================
load_dotenv()

# PolyTape (History) API
POLYTAPE_URL = "https://api.polytape.xyz"
POLYTAPE_KEY = os.getenv("POLYTAPE_API_KEY", "your_api_key_here")

# Polymarket (Metadata) API
GAMMA_API_URL = "https://gamma-api.polymarket.com/events/slug"

# Settings
EVENT_SLUG = "elon-musk-of-tweets-january-29-january-31"
TWEETS_FILE = "elon_musk_past_tweets.json"
OUTPUT_DIR = "tweet_market_impact_data"

# Date Filter (Inclusive)
START_DATE = datetime(2026, 1, 29).date()
END_DATE = datetime(2026, 1, 31).date()

# ==========================================
# API CLIENTS
# ==========================================

class PolyTapeClient:
    def __init__(self, base_url, api_key):
        self.url = base_url
        self.headers = {"x-api-key": api_key, "Content-Type": "application/json"}

    def get_historical_orderbook(self, asset_id, timestamp_ms):
        """
        Fetches the orderbook at a specific historical timestamp (Integer Milliseconds).
        timestamp_ms: 1769872555379 (int)
        """
        endpoint = f"{self.url}/v1/markets/{asset_id}/orderbook"
        
        # Send as integer in query params
        params = {"timestamp": timestamp_ms}
        
        try:
            r = requests.get(endpoint, headers=self.headers, params=params)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print(f"⚠️ Failed to fetch {asset_id} at {timestamp_ms}: {e}")
            return None

def get_assets_from_slug(slug):
    """Resolves an Event Slug to a list of Asset IDs (Token IDs) using Gamma API."""
    url = f"{GAMMA_API_URL}/{slug}"
    print(f"🔍 Resolving Slug: {slug}...")
    
    try:
        r = requests.get(url)
        r.raise_for_status()
        data = r.json()
        
        asset_ids = []
        markets = data.get("markets", [])
        
        for market in markets:
            clob_ids = market.get("clobTokenIds", [])
            if isinstance(clob_ids, str):
                clob_ids = json.loads(clob_ids)
            asset_ids.extend(clob_ids)
            
        print(f"✅ Found {len(asset_ids)} assets for this event.")
        return asset_ids
    except Exception as e:
        print(f"❌ Error resolving slug: {e}")
        return []

# ==========================================
# MAIN LOGIC
# ==========================================

def main():
    # 1. Setup
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    api = PolyTapeClient(POLYTAPE_URL, POLYTAPE_KEY)

    # 2. Get Asset IDs for the Event
    target_assets = get_assets_from_slug(EVENT_SLUG)
    if not target_assets:
        print("❌ No assets found. Exiting.")
        return

    # 3. Load Tweets
    try:
        with open(TWEETS_FILE, "r", encoding="utf-8") as f:
            tweets = json.load(f)
    except FileNotFoundError:
        print(f"❌ Could not find {TWEETS_FILE}")
        return

    print(f"📂 Loaded {len(tweets)} tweets. Filtering for Jan 29 - Jan 31...")

    # 4. Process Tweets
    processed_count = 0
    
    for tweet in tweets:
        tweet_id = tweet.get("id") or tweet.get("platformId")
        created_at_str = tweet.get("createdAt")
        
        if not created_at_str:
            continue

        # Parse ISO Date
        tweet_dt = date_parser.parse(created_at_str)
        
        # Filter Date Range
        if not (START_DATE <= tweet_dt.date() <= END_DATE):
            continue
            
        # --- KEY CHANGE: Convert to Integer Milliseconds ---
        # timestamp() returns seconds (float), multiply by 1000 and cast to int
        timestamp_ms = int(tweet_dt.timestamp() * 1000)

        processed_count += 1
        print(f"\n🐦 Processing Tweet {tweet_id} | Time: {created_at_str} | TS: {timestamp_ms}")

        # Create Folder for this specific tweet
        tweet_dir = os.path.join(OUTPUT_DIR, f"tweet_{tweet_id}")
        if not os.path.exists(tweet_dir):
            os.makedirs(tweet_dir)

        # 5. Fetch Orderbook for EVERY asset at this timestamp
        for asset_id in target_assets:
            save_path = os.path.join(tweet_dir, f"asset_{asset_id}.json")
            if os.path.exists(save_path):
                print(f"   Using cached: {asset_id}")
                continue

            # Fetch using the integer timestamp
            ob_data = api.get_historical_orderbook(asset_id, timestamp_ms)
            
            if ob_data:
                with open(save_path, "w") as f:
                    json.dump(ob_data, f, indent=2)
                print(f"   ✅ Saved snapshot: {asset_id}")
            
            # Rate limit
            time.sleep(0.1) 

    print(f"\n🎉 Finished! Processed {processed_count} tweets.")

if __name__ == "__main__":
    main()