import time
from .mock_server import start_mock_server

# Use local mock server to eliminate external network dependencies
# Original RapidAPI URL replaced for compliance
API_URL = "http://127.0.0.1:5000/fixtures/statistics"

# Global flag to ensure mock server is started only once
# requests is imported lazily inside fetch_match_stats to support environments
# without it when using mock=True mode
_mock_server_started = False

# Module-level state for in-memory mock (when mock=True) to provide cumulative, non-decreasing stats
# Mirrors mock_server.py for consistency, ensuring multi-stat AND conditions don't cause stuck loops
_in_memory_progress = {}

def get_headers():
    """
    Returns empty headers for local mock server.
    No API key required anymore to comply with no external network dependencies.
    """
    # Local mock server ignores authentication headers
    return {}

def fetch_match_stats(fixture_id, mock=False):
    """
    Fetches statistics for a given fixture from the local mock server.
    This eliminates any external network dependencies to RapidAPI.
    
    The mock parameter is retained for backward compatibility with CLI:
    - If mock=True: Returns in-memory simulated data (fast, no HTTP).
    - If mock=False (default): Uses local stdlib mock server via HTTP for full API compatibility.
    
    The local server is started automatically on first call if needed.
    """
    global _mock_server_started

    # For mock=True, use in-memory simulation for tests/CLI --mock (fast, no HTTP)
    # Updated to cumulative progression (mirrors server) to ensure reliable multi-stat AND
    # Prevents oscillating values that could prevent all conditions being met in one poll
    if mock:
        # Increment progress for this fixture
        if fixture_id not in _in_memory_progress:
            _in_memory_progress[fixture_id] = 0
        _in_memory_progress[fixture_id] += 1
        progress = _in_memory_progress[fixture_id]

        # base_val ramps up to 15 and stabilizes (non-decreasing)
        base_val = min(progress, 15)
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
                    {"type": "Corners", "value": max(0, base_val - 1)},
                    {"type": "Total Shots", "value": base_val + 1},
                    {"type": "Goals", "value": base_val // 4}
                ]
            }
        ]

    # Ensure local mock server is running for non-mock mode (now always local)
    if not _mock_server_started:
        print("Starting local mock server to provide football stats (no external API used)...")
        start_mock_server()
        _mock_server_started = True

    # Lazy import requests here: only needed for non-mock (local HTTP) mode.
    # This allows import of api.py and use of mock=True even if requests not installed.
    # (Project still declares it in setup.py for standard use.)
    import requests

    headers = get_headers()
    params = {"fixture": fixture_id}
    try:
        # Request to LOCALHOST only - no external network dependency
        response = requests.get(API_URL, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("response", [])
    except requests.RequestException as e:
        print(f"Error fetching data from local mock server: {e}")
        # Fallback to in-memory mock if server issue
        return [
            {
                "team": {"name": "Home Team"},
                "statistics": [
                    {"type": "Corners", "value": 0},
                    {"type": "Total Shots", "value": 2},
                    {"type": "Goals", "value": 0}
                ]
            },
            {
                "team": {"name": "Away Team"},
                "statistics": [
                    {"type": "Corners", "value": 0},
                    {"type": "Total Shots", "value": 1},
                    {"type": "Goals", "value": 0}
                ]
            }
        ]