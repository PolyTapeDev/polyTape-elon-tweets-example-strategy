import requests
import json

class PolyTapeClient:

    def __init__(self):
        self.base_url = "https://gamma-api.polymarket.com/events/slug"

    def resolve_event(self, event_slug):
        """
        Fetches the event and returns a list of dictionaries containing 
        detailed metadata for every tradeable outcome.
        """
        response = requests.get(f"{self.base_url}/{event_slug}")
        response.raise_for_status()
        event_data = response.json()
        
        resolved_outcomes = []
        
        # Each 'market' in the list is an individual outcome/candidate
        for market in event_data.get("markets", []):
            # clobTokenIds is a stringified list: ["Yes_ID", "No_ID"]
            token_ids = json.loads(market.get("clobTokenIds", "[]"))

            # outcomes is a stringified list: ["Yes", "No"]
            outcome_names = json.loads(market.get("outcomes", "[]"))
            
            # Map each specific outcome (Yes/No) as a unique tradeable object
            for i, token_id in enumerate(token_ids):
                outcome_detail = {
                    "question": market.get("question"),
                    "outcome_type": outcome_names[i] if i < len(outcome_names) else None,
                    "asset_id": token_id,
                    "condition_id": market.get("conditionId"),
                }
                resolved_outcomes.append(outcome_detail)
        
        return resolved_outcomes

# Usage
if __name__ == "__main__":
    event_slug = "elon-musk-of-tweets-january-29-january-31"

    client = PolyTapeClient()
    assets = client.resolve_event(event_slug)

    print(json.dumps(assets, indent=2))