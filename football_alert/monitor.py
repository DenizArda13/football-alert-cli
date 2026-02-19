import time
from .api import fetch_match_stats

def check_single_fixture(fixture_id, stat_name, team_name, target, mock=False):
    """
    Checks a single fixture for a specific condition.
    Returns True if alert triggered, False otherwise.
    """
    data = fetch_match_stats(fixture_id, mock=mock)
    
    if not data:
        return False

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
                        print(f"ALERT: The {team_name} has reached {current_value} {stat_name.lower()} in fixture {fixture_id}.")
                        return True
    return False

def start_monitoring(configs, interval=60, mock=False):
    """
    Monitors multiple match configurations simultaneously.
    configs: List of dicts -> [{'fixture_id': 123, 'stat': 'Corners', 'team': 'Home', 'target': 5}, ...]
    """
    print(f"Starting multi-monitor for fixtures {[c['fixture_id'] for c in configs]}. Press Ctrl+C to stop.")
    
    # Track which alerts have already triggered to avoid spamming
    triggered_configs = [False] * len(configs)

    try:
        while True:
            all_triggered = True
            
            for idx, config in enumerate(configs):
                if triggered_configs[idx]:
                    continue  # Skip if already triggered
                
                result = check_single_fixture(
                    config['fixture_id'], 
                    config['stat'], 
                    config['team'], 
                    config['target'], 
                    mock
                )
                
                if result:
                    triggered_configs[idx] = True
                else:
                    all_triggered = False
            
            if all_triggered:
                print("All alerts triggered across fixtures. Stopping monitor.")
                break

            time.sleep(interval)
            
    except KeyboardInterrupt:
        print("\nMonitoring stopped by user.")