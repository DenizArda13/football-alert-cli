import os
import requests
import random
import time

API_URL = "https://v3.football.api-sports.io/fixtures/statistics"

def get_headers():
    """Retrieves API key from environment variables."""
    api_key = os.getenv("FOOTBALL_API_KEY")
    if not api_key:
        return {}
    return {
        "x-rapidapi-host": "v3.football.api-sports.io",
        "x-rapidapi-key": api_key
    }

def fetch_match_stats(fixture_id, mock=False):
    """
    Fetches statistics for a given fixture.
    If mock is True, returns simulated data.
    """
    if mock:
        # Simulate stats increasing over time for demo purposes
        # Using time to simulate incremental progress
        base_val = int(time.time()) % 10  
        return [
            {
                "team": {"name": "Home Team"},
                "statistics": [
                    {"type": "Corners", "value": base_val},
                    {"type": "Total Shots", "value": base_val + 2},
                    {"type": "Goals", "value": base_val // 3}
                ]
            },
            {
                "team": {"name": "Away Team"},
                "statistics": [
                    {"type": "Corners", "value": base_val - 1 if base_val > 0 else 0},
                    {"type": "Total Shots", "value": base_val + 1},
                    {"type": "Goals", "value": base_val // 4}
                ]
            }
        ]

    headers = get_headers()
    if not headers:
        raise ValueError("API Key not found. Please set FOOTBALL_API_KEY environment variable.")

    params = {"fixture": fixture_id}
    try:
        response = requests.get(API_URL, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("response", [])
    except requests.RequestException as e:
        print(f"Error fetching data: {e}")
        return []