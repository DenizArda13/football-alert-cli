"""
History module for saving and loading tracking session data.
Saves completed fixture tracking sessions to a local history.json file.
"""

import json
import os
from datetime import datetime
from pathlib import Path

# Default history file location (in user's home directory for persistence)
DEFAULT_HISTORY_FILE = Path.home() / ".football_alert_history.json"


def get_history_file():
    """Get the path to the history file."""
    return DEFAULT_HISTORY_FILE


def load_history():
    """
    Load the history from the JSON file.
    Returns a list of session records, or empty list if file doesn't exist.
    """
    history_file = get_history_file()
    if not history_file.exists():
        return []
    
    try:
        with open(history_file, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def save_history(history_data):
    """
    Save the history to the JSON file.
    """
    history_file = get_history_file()
    with open(history_file, 'w') as f:
        json.dump(history_data, f, indent=2)


def save_session(session_data):
    """
    Save a completed tracking session to history.
    
    session_data should be a dict with:
    - session_id: unique identifier for the session
    - start_time: when monitoring started
    - end_time: when monitoring ended
    - fixtures: list of fixture tracking records
    """
    history = load_history()
    history.append(session_data)
    save_history(history)
    return len(history)


def create_session_record(fixture_id, conditions, alert_triggered, alert_minute=None, match_finished=False):
    """
    Create a record for a single fixture tracking session.
    
    Args:
        fixture_id: The fixture ID being tracked
        conditions: List of condition dicts (stat, team, target)
        alert_triggered: Whether an alert was triggered
        alert_minute: Minute when alert was triggered (if any)
        match_finished: Whether the match finished (90')
    
    Returns:
        Dict with fixture tracking details
    """
    return {
        "fixture_id": fixture_id,
        "conditions": [
            {
                "stat": cond.get("stat"),
                "team": cond.get("team"),
                "target": cond.get("target"),
                "met": cond.get("met", False),
                "minute_met": cond.get("minute_met")
            }
            for cond in conditions
        ],
        "alert_triggered": alert_triggered,
        "alert_minute": alert_minute,
        "match_finished": match_finished
    }


def get_fixture_name(fixture_id):
    """
    Get the fixture team names from the mock fixtures list.
    Returns a formatted string like "Home Team vs Away Team".
    """
    from .mock_server import get_mock_fixtures
    
    fixtures = get_mock_fixtures()
    for fixture in fixtures:
        if str(fixture["fixture_id"]) == str(fixture_id):
            return f"{fixture['home_team']} vs {fixture['away_team']}"
    return f"Fixture {fixture_id}"


def format_history_entry(entry, index):
    """
    Format a history entry for display.
    Returns a formatted string for the Rich UI.
    """
    lines = []
    
    # Session header
    session_time = entry.get("start_time", "Unknown")
    if session_time and session_time != "Unknown":
        try:
            dt = datetime.fromisoformat(session_time)
            session_time = dt.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            pass
    
    lines.append(f"Session #{index + 1} - {session_time}")
    
    # Fixtures tracked
    fixtures = entry.get("fixtures", [])
    for fixture in fixtures:
        fixture_id = fixture.get("fixture_id", "Unknown")
        fixture_name = get_fixture_name(fixture_id)
        alert_triggered = fixture.get("alert_triggered", False)
        alert_minute = fixture.get("alert_minute")
        match_finished = fixture.get("match_finished", False)
        
        status = "✅ ALERT" if alert_triggered else ("❌ Unmet" if match_finished else "⏳ Incomplete")
        minute_str = f"{alert_minute}'" if alert_minute else ("90'" if match_finished else "—")
        
        lines.append(f"  📋 {fixture_name} (ID: {fixture_id})")
        lines.append(f"     Status: {status} at {minute_str}")
        
        # Conditions
        conditions = fixture.get("conditions", [])
        for cond in conditions:
            stat = cond.get("stat", "Unknown")
            team = cond.get("team", "Unknown")
            target = cond.get("target", 0)
            met = cond.get("met", False)
            minute_met = cond.get("minute_met")
            
            met_str = "✓" if met else "✗"
            minute_str = f"({minute_met}')" if minute_met else ""
            lines.append(f"     - {team} {stat} >= {target}: {met_str} {minute_str}")
    
    return "\n".join(lines)


def clear_history():
    """
    Clear all history data.
    """
    history_file = get_history_file()
    if history_file.exists():
        history_file.unlink()
    return True
