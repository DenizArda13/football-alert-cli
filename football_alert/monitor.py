import time
import threading
from datetime import datetime
from collections import defaultdict
from .api import fetch_match_stats
from . import dashboard

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


def check_all_conditions_for_fixture(fixture_id, conditions, mock=False, use_dashboard=False):
    """
    Checks a fixture against multiple conditions (for multi-stat tracking).
    conditions: list of dicts e.g., [{'stat': 'Corners', 'team': 'Home Team', 'target': 3}, ...]
    Returns True ONLY if ALL conditions are met simultaneously (AND logic).
    Fetches stats AND elapsed minute once per call for efficiency. Prints unified alert
    in the EXACT required format (no fixture ID; uses target value; minute with '; separator for multi-stat).
    use_dashboard: if True, updates the dashboard instead of printing alerts.
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
                        # Update dashboard with current stat (if enabled)
                        if use_dashboard:
                            dashboard.update_fixture_stat(
                                fixture_id, stat_name, team_name, current_value, target, elapsed
                            )
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
        if use_dashboard:
            dashboard.mark_alert_triggered(fixture_id)
        else:
            print(f"🚨 ALERT: {alert_details}")
        return True
    return False


def _monitor_fixture(fixture_id, conditions, interval, mock, shutdown_event, use_dashboard=False):
    """
    Private helper for per-fixture monitoring in a dedicated thread.
    Runs independent loop until:
    - Alert is triggered (all conditions met), OR
    - Match finishes (elapsed >= 90 minutes), OR
    - Shutdown event is set (Ctrl+C)
    
    Enables true concurrency so fixtures don't block each other.
    Alert printed in exact spec format by check_all_conditions_for_fixture.
    use_dashboard: if True, updates dashboard instead of printing alerts.
    """
    triggered = False
    match_finished = False
    
    while not triggered and not match_finished and not shutdown_event.is_set():
        # check_all_conditions_for_fixture handles AND logic for multi-stat
        # Prints alert on trigger in required format (e.g., with ; for multi-stat)
        if check_all_conditions_for_fixture(fixture_id, conditions, mock, use_dashboard=use_dashboard):
            triggered = True
        else:
            # Check if match has finished (elapsed >= 90) in dashboard mode
            if use_dashboard:
                with dashboard._dashboard_lock:
                    if fixture_id in dashboard._fixture_stats:
                        match_finished = dashboard._fixture_stats[fixture_id]['match_finished']
            
            # Sleep in thread; interruptible via event
            time.sleep(interval)

    if shutdown_event.is_set():
        return  # Graceful exit on Ctrl+C


def _all_fixtures_done(fixture_ids, use_dashboard=False):
    """
    Check if all fixtures are done monitoring.
    A fixture is done when:
    - Alert is triggered (all conditions met), OR
    - Match is finished (elapsed >= 90 minutes)
    
    Returns True if all fixtures are done, False otherwise.
    """
    if not use_dashboard:
        # Without dashboard, we can't check status
        return False
    
    with dashboard._dashboard_lock:
        for fixture_id in fixture_ids:
            if fixture_id not in dashboard._fixture_stats:
                return False
            
            data = dashboard._fixture_stats[fixture_id]
            # Fixture is done if alert triggered OR match finished
            is_done = data['alert_triggered'] or data['match_finished']
            if not is_done:
                return False
    
    return True


def start_monitoring(configs, interval=60, mock=False, use_dashboard=False):
    """
    Monitors multiple match configurations *concurrently* using threads, with support for multiple statistics per fixture.
    configs: List of dicts -> [{'fixture_id': 123, 'stat': 'Corners', 'team': 'Home Team', 'target': 5}, ...]
    
    For multiple stats on the same fixture, all conditions must be met (AND logic) before triggering an alert.
    Now includes the match minute (from mock/server progression) when all thresholds are reached for the fixture.
    Each fixture runs in its own thread for independent/non-blocking monitoring (fixes synchronous loop blocking).
    Multi-fixture support is now truly parallel.
    
    Monitoring continues until:
    - ALL fixtures either trigger an alert OR reach match end (90 minutes) with unmet conditions, OR
    - User presses Ctrl+C for graceful shutdown
    
    use_dashboard: if True, displays a live-updating Rich terminal dashboard instead of console output.
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
    
    # Initialize dashboard if enabled
    if use_dashboard:
        dashboard.set_fixtures_count(len(unique_fixtures))
        # Pre-populate dashboard with all conditions to track
        for fixture_id, conditions in groups.items():
            dashboard.initialize_conditions(fixture_id, conditions)
    else:
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
            args=(fixture_id, conditions, interval, mock, shutdown_event, use_dashboard),
            daemon=True  # Threads auto-terminate when main exits
        )
        thread.start()
        threads.append(thread)
    
    if use_dashboard:
        # Run dashboard in main thread (Live display must run in main thread)
        # But we need to periodically check if all threads are done
        import sys
        console = dashboard._console if hasattr(dashboard, '_console') else None
        
        # Use a non-blocking approach: update dashboard and check threads
        dashboard._global_stats['monitoring'] = True
        dashboard._global_stats['start_time'] = datetime.now()
        dashboard._global_stats['fixtures_count'] = len(unique_fixtures)
        
        with dashboard.Live(dashboard._build_dashboard(), refresh_per_second=2, console=dashboard.Console()) as live:
            try:
                while dashboard._global_stats['monitoring']:
                    live.update(dashboard._build_dashboard())
                    
                    # Check if all threads are done
                    all_done = all(not thread.is_alive() for thread in threads)
                    if all_done:
                        dashboard._global_stats['monitoring'] = False
                    
                    time.sleep(0.5)
            except KeyboardInterrupt:
                shutdown_event.set()
                dashboard._global_stats['monitoring'] = False
    else:
        try:
            # Wait for all threads to complete
            # Each fixture monitors independently until:
            # - Alert triggered (all conditions met), OR
            # - Match finished (90 minutes, some conditions unmet)
            for thread in threads:
                thread.join()
            
            print("All fixtures finished monitoring. Stopping monitor.")
        except KeyboardInterrupt:
            # Signal shutdown to all threads
            shutdown_event.set()
            # Join with timeout to avoid hang
            for thread in threads:
                thread.join(timeout=1.0)
            print("\nMonitoring stopped by user.")