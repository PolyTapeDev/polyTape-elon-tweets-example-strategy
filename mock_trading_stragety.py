import os
import json
import time
import requests
import pandas as pd
from datetime import datetime, timedelta, timezone
from dateutil import parser as date_parser
from dotenv import load_dotenv

# ==========================================
# ⚙️ CONFIGURATION
# ==========================================
STRATEGY_NAME = "Short_The_Winner_Verbose_Log"
INITIAL_CAPITAL = 10000.0
HOLD_TIME_MINUTES = 60 * 24
BUY_DELAY_SECONDS = 5
MAX_TRADE = 30
BUY_AMONUT = 1000.0

# Date Filter (UTC)
START_DT = datetime(2026, 1, 29, 0, 0, 0, tzinfo=timezone.utc)
END_DT   = datetime(2026, 1, 31, 23, 59, 59, tzinfo=timezone.utc)

# Files
TWEETS_FILE = "elon_musk_past_tweets.json"
MARKET_MAP_FILE = "elon_musk_event_data.json"
CACHE_DIR = "backtest_cache"

# API
load_dotenv()
POLYTAPE_URL = "https://api.polytape.xyz"
POLYTAPE_KEY = os.getenv("POLYTAPE_API_KEY")

class BacktestEngine:
    def __init__(self):
        self.headers = {"x-api-key": POLYTAPE_KEY, "Content-Type": "application/json"}
        self.equity = INITIAL_CAPITAL
        self.history = []
        self.market_map = self._load_market_map()

    def _load_market_map(self):
        if not os.path.exists(MARKET_MAP_FILE):
            print(f"❌ Error: {MARKET_MAP_FILE} not found!")
            return {}

        with open(MARKET_MAP_FILE, 'r') as f:
            data = json.load(f)

        mapping = {}
        for item in data:
            q = item.get('question')
            outcome = item.get('outcome_type')
            aid = item.get('asset_id')
            
            if q not in mapping:
                mapping[q] = {}
            mapping[q][outcome] = aid
        
        print(f"✅ Loaded {len(mapping)} outcome buckets from map.")
        return mapping

    def get_orderbook(self, asset_id, timestamp_ms):
        if not os.path.exists(CACHE_DIR): os.makedirs(CACHE_DIR)
        cache_path = f"{CACHE_DIR}/asset_{asset_id}_{timestamp_ms}.json"
        
        if os.path.exists(cache_path):
            with open(cache_path, 'r') as f: return json.load(f)
            
        try:
            url = f"{POLYTAPE_URL}/v1/markets/{asset_id}/orderbook"
            r = requests.get(url, headers=self.headers, params={"timestamp": timestamp_ms})
            if r.status_code == 200:
                data = r.json()
                with open(cache_path, 'w') as f: json.dump(data, f)
                time.sleep(0.1)
                return data
        except Exception:
            pass
        return None

    def get_price_from_ob(self, ob, side='buy'):
        if not ob: return 0.0
        target = ob.get('asks' if side == 'buy' else 'bids', [])
        if not target: return 0.0
        first = target[0]
        try:
            return float(first[0]) if isinstance(first, list) else float(first.get('price'))
        except:
            return 0.0

    def execute_order(self, orderbook, side, amount):
        """
        Executes an order against the book.
        Returns: (average_price, amount_acquired, levels_consumed)
        """
        if not orderbook: return None, 0, 0

        target = orderbook.get('asks' if side == 'buy' else 'bids', [])
        levels = []
        for x in target:
            try: levels.append({'p': float(x[0]), 's': float(x[1])})
            except: continue
        
        # Sort: Low to High for Buys (Asks), High to Low for Sells (Bids)
        levels.sort(key=lambda x: x['p'], reverse=(side == 'sell'))

        spent = 0.0
        acquired = 0.0
        remaining = amount
        levels_consumed = 0

        for lvl in levels:
            levels_consumed += 1
            p, s = lvl['p'], lvl['s']
            
            # For BUYs: Capacity is size * price (how much USD we can spend here)
            # For SELLs: Capacity is size (how many shares people want to buy)
            capacity = (s * p) if side == 'buy' else s
            
            take = min(remaining, capacity)
            
            if side == 'buy':
                shares = take / p
                spent += take
                acquired += shares
            else:
                usd = take * p
                spent += take 
                acquired += usd 
                
            remaining -= take
            if remaining <= 0: break

        # Check if we filled at least 99% of the order
        if remaining > amount * 0.01: 
            return None, 0, 0
            
        avg_price = (spent / acquired) if side == 'buy' else (acquired / spent)
        return avg_price, acquired, levels_consumed

    def run(self):
        print(f"🚀 Strategy: {STRATEGY_NAME}")
        
        with open(TWEETS_FILE, 'r') as f:
            all_tweets = json.load(f)

        target_tweets = [t for t in all_tweets if t.get('createdAt') and START_DT <= date_parser.parse(t['createdAt']) <= END_DT]
        target_tweets.sort(key=lambda x: date_parser.parse(x['createdAt']))
        
        target_tweets = target_tweets[:MAX_TRADE]
        
        print(f"🎯 Found {len(target_tweets)} tweets. Starting analysis...")
        print("-" * 60)

        for i, tweet in enumerate(target_tweets):
            tid = tweet.get('platformId')
            created_at = tweet.get('createdAt')
            dt_obj = date_parser.parse(created_at)
            
            ts_entry = int((dt_obj + timedelta(seconds=BUY_DELAY_SECONDS)).timestamp() * 1000)
            ts_exit  = int((dt_obj + timedelta(minutes=HOLD_TIME_MINUTES)).timestamp() * 1000)
            tweet_url = f"https://x.com/elonmusk/status/{tid}"

            print(f"\n🐦 Trade {i+1} | {created_at}")
            print(f"   🔗 Found Elon Tweet: {tweet_url}")

            # ----------------------------------------------------
            # 1. MARKET SCAN
            # ----------------------------------------------------
            print(f"   🔍 Scanning {len(self.market_map)} outcome buckets for the leader...")
            
            best_question = None
            highest_yes_price = -1.0
            
            for question, assets in self.market_map.items():
                yes_id = assets.get('Yes')
                if not yes_id: continue
                
                ob_yes = self.get_orderbook(yes_id, ts_entry)
                current_price = self.get_price_from_ob(ob_yes, side='buy')
                
                short_q = (question[:50] + '..') if len(question) > 50 else question
                print(f"      👉 Checking: '{short_q}' | Price: ${current_price:.2f}")

                if current_price > highest_yes_price:
                    highest_yes_price = current_price
                    best_question = question

            if not best_question or highest_yes_price < 0.10:
                print("   ⚠️  No clear favorite found (Liquidity low?). Skipping.")
                continue
            
            print(f"   🏆 Leader Found: '{best_question}' (Price: ${highest_yes_price:.2f})")
            
            # ----------------------------------------------------
            # 2. EXECUTION
            # ----------------------------------------------------
            target_no_id = self.market_map[best_question].get('No')
            print(f"   📉 Action: Buying 'NO' on the leader (Shorting).")

            # Buy NO
            ob_no_entry = self.get_orderbook(target_no_id, ts_entry)
            buy_price, shares, buy_levels = self.execute_order(ob_no_entry, 'buy', BUY_AMONUT)

            if not buy_price:
                print("      🚫 Entry Failed: No liquidity for NO side.")
                continue
            
            # Calc Slippage info
            theoretical_no = 1.0 - highest_yes_price
            slippage = buy_price - theoretical_no
            print(f"      🔸 Spread Info:  YES=${highest_yes_price:.2f} implies NO should be ~${theoretical_no:.2f}")
            print(f"      🔵 EXECUTE BUY NO @ ${buy_price:.3f} | Shares: {shares:.1f} | Levels Hit: {buy_levels} | Slippage: +${slippage:.3f}")

            # Sell NO
            ob_no_exit = self.get_orderbook(target_no_id, ts_exit)
            sell_price, cash_back, sell_levels = self.execute_order(ob_no_exit, 'sell', shares)

            if not sell_price:
                print("      🚫 Exit Failed (Illiquid). Marking as Loss.")
                pnl = -1000.0
            else:
                pnl = cash_back - 1000.0
                print(f"      🔴 EXECUTE SELL NO @ ${sell_price:.3f} | Cash: ${cash_back:.2f} | Levels Hit: {sell_levels}")

            self.equity += pnl
            print(f"   💸 PnL: ${pnl:+.2f} | Equity: ${self.equity:,.2f}")
            print("-" * 60)
            
            self.history.append({
                "time": created_at,
                "tweet_link": tweet_url,
                "target": best_question,
                "pnl": pnl
            })

        if self.history:
            df = pd.DataFrame(self.history)
            print("\n" + "="*30)
            print(f"Total PnL: ${df['pnl'].sum():.2f}")
            print(f"Final Eq:  ${self.equity:,.2f}")
            print("="*30)

if __name__ == "__main__":
    engine = BacktestEngine()
    engine.run()