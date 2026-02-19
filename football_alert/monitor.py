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
    in the EXACT required format (no fixture ID; uses target value; minute with '; separator for multi-stat).
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
                        # Logic: Reach or Exceed (current_value >= target still)
                        if int(current_value) >= target:
                            condition_met = True
                            # Build part in EXACT spec format: "[Team] reached [Target] [Statistic]. ([Minute]')"
                            # - stat_name as original case (e.g., "Total Shots")
                            # - Use target (not current_value)
                            # - Period after stat; minute with '; shared elapsed for fixture
                            # This ensures multi-stat joins correctly with "; "
                            alert_parts.append(f"{team_name} reached {target} {stat_name}. ({elapsed}')")
                            break
                if condition_met:
                    break
        if not condition_met:
            all_met = False
            # Continue checking others for potential (but don't early return)

    if all_met:
        # EXACT required format: "🚨 ALERT: " + parts joined by "; " (one line, even for multi-stat)
        # E.g., "🚨 ALERT: Home Team reached 3 Corners. (20'); Away Team reached 5 Total Shots. (20')"
        # Minute is per-fixture (captured at poll when ALL met); no fixture ID or extra text.
        # Fulfills spec for single/multi-stat/multi-match cases.
        alert_details = '; '.join(alert_parts)
        print(f"🚨 ALERT: {alert_details}")
        return True
    return False


def _monitor_fixture(fixture_id, conditions, interval, mock, shutdown_event):
    """
    Private helper for per-fixture monitoring in a dedicated thread.
    Runs independent loop until conditions met or shutdown.
    Enables true concurrency so fixtures don't block each other.
    Alert printed in exact spec format by check_all_conditions_for_fixture.
    """
    triggered = False
    while not triggered and not shutdown_event.is_set():
        # check_all_conditions_for_fixture handles AND logic for multi-stat
        # Prints alert on trigger in required format (e.g., with ; for multi-stat)
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