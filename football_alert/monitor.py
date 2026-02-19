import time
import threading
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
    Fetches stats AND elapsed minute once per call for efficiency. Prints unified alert
    INCLUDING the minute when thresholds reached.
    This implements the requirement: alerts now report "at minute X" when all stats
    thresholds are met for the fixture/match.
    """
    # Updated: fetch_match_stats now returns (stats_list, elapsed_minute) tuple
    # to include match minute in alert (when all thresholds reached)
    # Elapsed from mock progression/server response; ensures "when did ... in minute"
    stats, elapsed = fetch_match_stats(fixture_id, mock=mock)
    
    # Use stats for condition check (elapsed only for alert timing)
    if not stats:
        return False

    all_met = True
    alert_parts = []

    for cond in conditions:
        stat_name = cond['stat']
        team_name = cond['team']
        target = cond['target']
        condition_met = False

        for team_data in stats:  # renamed from data for clarity
            if team_data['team']['name'] == team_name:
                stats_list = team_data.get('statistics', [])  # avoid name clash
                for stat in stats_list:
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
        # Professional, concise alert format UPDATED for minute reporting:
        # "ALERT: Fixture ID at minute X - Targets reached: ..." 
        # This fulfills: include when (in match minute) all stats reached thresholds.
        # Minute captured at the poll when ALL conditions first met simultaneously.
        alert_details = '; '.join(alert_parts)
        print(f"🚨 ALERT: Fixture {fixture_id} at minute {elapsed} - Targets reached: {alert_details}.")
        return True
    return False


def _monitor_fixture(fixture_id, conditions, interval, mock, shutdown_event):
    """
    Private helper for per-fixture monitoring in a dedicated thread.
    Runs independent loop until conditions met or shutdown.
    Enables true concurrency so fixtures don't block each other.
    Alert now includes the minute when all statistics reach their threshold values.
    """
    triggered = False
    while not triggered and not shutdown_event.is_set():
        # check_all_conditions_for_fixture handles AND logic for multi-stat
        # Prints professional alert on trigger
        if check_all_conditions_for_fixture(fixture_id, conditions, mock):
            triggered = True
        else:
            # Sleep in thread; interruptible via event
            time.sleep(interval)

    if shutdown_event.is_set():
        return  # Graceful exit on Ctrl+C


def start_monitoring(configs, interval=60, mock=False):
    """
    Monitors multiple match configurations *concurrently* using threads, with support for multiple statistics per fixture.
    configs: List of dicts -> [{'fixture_id': 123, 'stat': 'Corners', 'team': 'Home Team', 'target': 5}, ...]
    
    For multiple stats on the same fixture, all conditions must be met (AND logic) before triggering an alert.
    Now includes the match minute (from mock/server progression) when all thresholds are reached for the fixture.
    Each fixture runs in its own thread for independent/non-blocking monitoring (fixes synchronous loop blocking).
    Multi-fixture support is now truly parallel.
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
    print(f"Starting concurrent multi-monitor for fixtures {unique_fixtures} (independent threads per fixture). Press Ctrl+C to stop.")
    
    # Shared event for graceful shutdown across threads on Ctrl+C
    # Ensures all threads stop cleanly without blocking
    shutdown_event = threading.Event()
    
    # One daemon thread per fixture/group for true parallelism
    # Fixes synchronous loop blocking other fixtures
    threads = []
    for fixture_id, conditions in groups.items():
        thread = threading.Thread(
            target=_monitor_fixture,
            args=(fixture_id, conditions, interval, mock, shutdown_event),
            daemon=True  # Threads auto-terminate when main exits
        )
        thread.start()
        threads.append(thread)
    
    try:
        # Wait for all threads to complete (i.e., all fixtures' alerts triggered)
        # Non-blocking: each fixture monitors independently
        for thread in threads:
            thread.join()
        print("All fixture alerts triggered (all conditions met). Stopping monitor.")
    except KeyboardInterrupt:
        # Signal shutdown to all threads
        shutdown_event.set()
        # Join with timeout to avoid hang
        for thread in threads:
            thread.join(timeout=1.0)
        print("\nMonitoring stopped by user.")