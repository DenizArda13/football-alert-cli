import time
from collections import defaultdict
from .api import fetch_match_stats

def check_single_fixture(fixture_id, stat_name, team_name, target, mock=False):
    """
    Checks a single fixture for a specific condition.
    Returns True if alert triggered, False otherwise.
    (Retained for backward compatibility and single-stat cases.)
    """
    # Delegate to multi-condition checker (handles single as group of 1)
    return check_all_conditions_for_fixture(
        fixture_id, 
        [{'stat': stat_name, 'team': team_name, 'target': target}], 
        mock
    )


def check_all_conditions_for_fixture(fixture_id, conditions, mock=False):
    """
    Checks a fixture against multiple conditions (for multi-stat tracking).
    conditions: list of dicts e.g., [{'stat': 'Corners', 'team': 'Home Team', 'target': 3}, ...]
    Returns True ONLY if ALL conditions are met simultaneously (AND logic).
    Fetches stats once per call for efficiency. Prints unified alert.
    This implements the requirement: alerts trigger only when all specified stats have been met.
    """
    data = fetch_match_stats(fixture_id, mock=mock)
    
    if not data:
        return False

    all_met = True
    alert_parts = []

    for cond in conditions:
        stat_name = cond['stat']
        team_name = cond['team']
        target = cond['target']
        condition_met = False

        for team_data in data:
            if team_data['team']['name'] == team_name:
                stats = team_data.get('statistics', [])
                for stat in stats:
                    if stat['type'] == stat_name:
                        current_value = stat['value']
                        if current_value is None:
                            continue
                        # Logic: Reach or Exceed
                        if int(current_value) >= target:
                            condition_met = True
                            alert_parts.append(f"{team_name} reached {current_value} {stat_name.lower()}")
                            break
                if condition_met:
                    break
        if not condition_met:
            all_met = False
            # Continue checking others for potential (but don't early return)

    if all_met:
        # Professional, concise alert format for multi-stat/multi-match scenarios
        # Structured as: "ALERT: Fixture ID - Team stat details" for clarity and professionalism
        # Avoids spam, focuses on key info (fixture, teams, achieved stats)
        alert_details = '; '.join(alert_parts)
        print(f"🚨 ALERT: Fixture {fixture_id} - Targets reached: {alert_details}.")
        return True
    return False

def start_monitoring(configs, interval=60, mock=False):
    """
    Monitors multiple match configurations simultaneously, with support for multiple statistics per fixture.
    configs: List of dicts -> [{'fixture_id': 123, 'stat': 'Corners', 'team': 'Home Team', 'target': 5}, ...]
    
    For multiple stats on the same fixture, all conditions must be met (AND logic) before triggering an alert.
    Multi-fixture support remains, with independent conditions per fixture.
    """
    # Group configs by fixture_id to enable per-fixture multi-stat AND logic
    # (Allows same fixture repeated for multiple stats, as per CLI options)
    groups = defaultdict(list)
    for config in configs:
        groups[config['fixture_id']].append({
            'stat': config['stat'],
            'team': config['team'],
            'target': config['target']
        })

    unique_fixtures = list(groups.keys())
    print(f"Starting multi-monitor for fixtures {unique_fixtures} (multi-stat AND per fixture). Press Ctrl+C to stop.")
    
    # Track which fixtures' alerts have already triggered to avoid spamming
    # Key: fixture_id, Value: triggered bool
    triggered_fixtures = {fid: False for fid in unique_fixtures}

    try:
        while True:
            all_triggered = True
            
            for fixture_id, conditions in groups.items():
                if triggered_fixtures[fixture_id]:
                    continue  # Skip if already triggered for this fixture/group
                
                # Use multi-condition check: True only if ALL stats met for the fixture
                result = check_all_conditions_for_fixture(
                    fixture_id, 
                    conditions, 
                    mock
                )
                
                if result:
                    triggered_fixtures[fixture_id] = True
                else:
                    all_triggered = False
            
            if all_triggered:
                print("All fixture alerts triggered (all conditions met). Stopping monitor.")
                break

            time.sleep(interval)
            
    except KeyboardInterrupt:
        print("\nMonitoring stopped by user.")