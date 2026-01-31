# ⚡ PolyTape: Professional Backtesting for Prediction Markets

**Don't just backtest price. Backtest reality.**

This project is a reference implementation of a **"Short-the-Winner"** strategy on Elon Musk's tweet frequency. It demonstrates how to use the **PolyTape API** to reconstruct historical order books, simulate granular execution, and uncover the hidden costs (slippage & spread) that basic price charts hide.

---

## 🎯 Target Market

This strategy is currently configured to trade the following specific Polymarket event:

* **Event:** "How many times will Elon Musk tweet? (Jan 29 - Jan 31)"
* **Slug:** `elon-musk-of-tweets-january-29-january-31`
* **URL:** [https://polymarket.com/event/elon-musk-of-tweets-january-29-january-31](https://polymarket.com/event/elon-musk-of-tweets-january-29-january-31)

*The code uses this specific event to demonstrate how PolyTape handles multi-outcome markets (buckets like "65-89", "90-114", etc.) and high-frequency volatility.*

---

## 📂 Data & Configuration Files

The strategy relies on three critical files to simulate the past and map it to market reality.

### 1. `elon_musk_past_tweets.json` (The Time Machine)

* **What it is:** A historical archive of Elon Musk’s X/Twitter activity.
* **Role:** Acts as the **Signal Source**. In the simulation, this file allows us to "replay" history, triggering trade logic at the exact second a tweet was posted.
* **Why it matters:** Precise timestamps are required to query PolyTape for the market state *immediately* following an event.

### 2. `elon_musk_event_data.json` (The Market Map)

* **What it is:** A mapping file that links human-readable market questions (e.g., *"Will Elon tweet 65-89 times?"*) to their specific **Polymarket Asset IDs** for the event slug mentioned above.
* **Role:** Acts as the **Resolution Layer**. The strategy uses this to know exactly which token ID to query via PolyTape when a specific scenario becomes the "favorite."
* **PolyTape Connection:** PolyTape requires these unique Asset IDs to fetch historical liquidity.

### 3. `strategy_output.txt` (The Evidence)

* **What it is:** A generated log file containing the full simulation results.
* **Role:** Acts as the **Proof of Execution**. It shows trade-by-trade breakdowns including:
* **Entry/Exit Prices:** Not just the "mid-price," but the actual weighted average price paid.
* **Liquidity Consumption:** How many levels of the order book were eaten by the trade size.
* **Slippage Analysis:** The cost difference between the theoretical price and the executed price.


* **Key Takeaway:** This file proves that strategies which look profitable on a simple chart might actually lose money once you account for the spread data provided by PolyTape.

---

## 🛠️ The Strategy Pipeline

This project is modular, separating data fetching from execution logic.

| Script | Description |
| --- | --- |
| **`fetch_polymarket_past_orderbook.py`** | **The Core Connector.** Takes an Asset ID and Timestamp  Returns the exact PolyTape Orderbook. This is the engine that makes the backtest "real." |
| **`mock_trading_stragety.py`** | **The Simulation Brain.** Iterates through the tweet history, identifies the "Winning" bucket, and executes phantom trades against the PolyTape data to calculate PnL. |
| **`get_elon_past_twitter_data.py`** | **The Signal Scraper.** Fetches the raw event data (tweets) used to populate the history file. |
| **`fetch_asset_id_data.py`** | **The Mapper.** Discovers active markets using the event slug and builds the `event_data.json` map. |

---

## 🚀 Why Use PolyTape?

Most backtests fail because they assume you can buy at the "last price." In prediction markets, liquidity is fragmented. **PolyTape** prevents false confidence by providing:

1. **Full Depth Replay:** See the bids/asks exactly as they were 5 seconds after a tweet.
2. **Slippage Reality Checks:** Calculate exactly how much a $1,000 order moves the price.
3. **High-Fidelity Timestamps:** Correlate external events (news, tweets) with market reaction down to the millisecond.

### Run the Simulation

```bash
# 1. Install Requirements
pip install -r requirements.txt

# 2. Add your PolyTape Key
echo "POLYTAPE_API_KEY=your_key" > .env

# 3. Start Trading
python mock_trading_stragety.py

```