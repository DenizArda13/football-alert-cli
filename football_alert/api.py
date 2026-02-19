import time
from .mock_server import start_mock_server, generate_mock_stats

# Use local mock server to eliminate external network dependencies
# Original RapidAPI URL replaced for compliance
API_URL = "http://127.0.0.1:5000/fixtures/statistics"

# Global flag to ensure mock server is started only once
# requests is imported lazily inside fetch_match_stats to support environments
# without it when using mock=True mode
_mock_server_started = False

# Global flag only for server start; in-memory mock now delegates to generate_mock_stats()
# from mock_server.py (single source of truth for cumulative stats + elapsed minute)

def get_headers():
    """
    Returns empty headers for local mock server.
    No API key required anymore to comply with no external network dependencies.
    """
    # Local mock server ignores authentication headers
    return {}

def fetch_match_stats(fixture_id, mock=False):
    """
    Fetches statistics AND elapsed minute for a given fixture from the local mock server.
    Updated to support reporting the match minute when all stats thresholds are reached.
    Returns: tuple (stats_list, elapsed_minute)  [BREAKING for callers; see monitor.py updates]
    
    This eliminates any external network dependencies to RapidAPI.
    
    The mock parameter is retained for backward compatibility with CLI:
    - If mock=True: Delegates to generate_mock_stats() for in-memory simulated data (fast, no HTTP).
      (Removed separate _in_memory_progress to avoid duplication; uses server's module state.)
    - If mock=False (default): Uses local stdlib mock server via HTTP for full API compatibility
      (now includes 'elapsed' in JSON).
    
    The local server is started automatically on first call if needed.
    Elapsed minute simulates match time (advances ~5 min per poll, caps at 90) for alert timing.
    """
    global _mock_server_started

    # For mock=True, use in-memory simulation via shared generator (fast, no HTTP)
    # Mirrors mock_server.py exactly for cumulative progression + elapsed minute
    # Ensures reliable multi-stat AND triggering and accurate minute in alerts
    # (Previously duplicated; now DRY for consistency)
    if mock:
        return generate_mock_stats(fixture_id)  # returns (stats, elapsed)

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
        # Extract stats (as before) and new elapsed minute for alert timing
        # 'elapsed' added by updated mock server/do_GET
        # Fallback to 0 if missing (for robustness)
        stats = data.get("response", [])
        elapsed = data.get("elapsed", 0)
        return stats, elapsed
    except requests.RequestException as e:
        print(f"Error fetching data from local mock server: {e}")
        # Fallback to in-memory mock if server issue (now includes elapsed=0)
        # Uses generator for consistency (advances progress but rare in error case)
        # Alternatively could hardcode, but ensures minute reported
        return generate_mock_stats(fixture_id)  # (stats, elapsed) even on error fallback