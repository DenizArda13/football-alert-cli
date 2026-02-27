"""
Live-updating terminal dashboard for football match monitoring using Rich library.
Displays real-time statistics, alerts, and monitoring status in a professional UI.
"""

import threading
import time
from collections import defaultdict
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text
from rich.live import Live
from rich.align import Align
from rich.spinner import Spinner

# Global dashboard state (thread-safe updates via locks)
_dashboard_lock = threading.Lock()
_fixture_stats = defaultdict(lambda: {
    'conditions': [],  # List of (stat_name, team_name, target)
    'current_values': {},  # Dict of team_stat -> current_value
    'met_conditions': {},  # Dict of (stat, team, target) -> minute_met (or None if not met)
    'alert_triggered': False,
    'alert_time': None,
    'alert_minute': None,  # Minute when alert was triggered
    'elapsed_minute': 0,
    'last_update': None,
    'match_finished': False  # True when elapsed_minute reaches 90
})

_global_stats = {
    'total_alerts': 0,
    'start_time': datetime.now(),
    'monitoring': True,
    'fixtures_count': 0
}


def update_fixture_stat(fixture_id, stat_name, team_name, current_value, target, elapsed_minute):
    """
    Updates the dashboard state with current fixture statistics.
    Called from the monitoring loop to reflect real-time data.
    Tracks when conditions are met and stores the minute they were met.
    """
    with _dashboard_lock:
        if stat_name and team_name:
            key = f"{team_name}_{stat_name}"
            _fixture_stats[fixture_id]['current_values'][key] = current_value
        
        _fixture_stats[fixture_id]['elapsed_minute'] = elapsed_minute
        _fixture_stats[fixture_id]['last_update'] = datetime.now()
        
        # Mark match as finished when elapsed reaches 90
        if elapsed_minute >= 90:
            _fixture_stats[fixture_id]['match_finished'] = True
        
        if stat_name and team_name:
            # Check if this condition is met and track the minute it was met
            cond_key = (stat_name, team_name, target)
            if cond_key not in _fixture_stats[fixture_id]['met_conditions']:
                _fixture_stats[fixture_id]['met_conditions'][cond_key] = None  # Not met yet
            
            # If condition is now met and wasn't before, record the minute
            if current_value is not None and int(current_value) >= target:
                if _fixture_stats[fixture_id]['met_conditions'][cond_key] is None:
                    _fixture_stats[fixture_id]['met_conditions'][cond_key] = elapsed_minute


def mark_alert_triggered(fixture_id):
    """Mark that an alert has been triggered for this fixture."""
    with _dashboard_lock:
        _fixture_stats[fixture_id]['alert_triggered'] = True
        _fixture_stats[fixture_id]['alert_time'] = datetime.now()
        _fixture_stats[fixture_id]['alert_minute'] = _fixture_stats[fixture_id]['elapsed_minute']
        _global_stats['total_alerts'] += 1


def set_fixtures_count(count):
    """Set the total number of fixtures being monitored."""
    with _dashboard_lock:
        _global_stats['fixtures_count'] = count


def initialize_conditions(fixture_id, conditions):
    """
    Initialize dashboard with conditions to track for a fixture.
    conditions: list of dicts [{'stat': 'Corners', 'team': 'Home Team', 'target': 3}, ...]
    """
    with _dashboard_lock:
        for cond in conditions:
            stat_name = cond['stat']
            team_name = cond['team']
            target = cond['target']
            cond_key = (stat_name, team_name, target)
            if cond_key not in _fixture_stats[fixture_id]['conditions']:
                _fixture_stats[fixture_id]['conditions'].append(cond_key)
            # Initialize met_conditions tracking for this condition
            if cond_key not in _fixture_stats[fixture_id]['met_conditions']:
                _fixture_stats[fixture_id]['met_conditions'][cond_key] = None


def stop_monitoring():
    """Signal that monitoring has stopped."""
    with _dashboard_lock:
        _global_stats['monitoring'] = False


def _build_stats_table():
    """Build the main statistics table."""
    table = Table(title="📊 Live Match Statistics", show_header=True, header_style="bold cyan")
    table.add_column("Fixture ID", style="magenta")
    table.add_column("Stat", style="cyan")
    table.add_column("Team", style="green")
    table.add_column("Current", style="yellow")
    table.add_column("Target", style="blue")
    table.add_column("Status", style="white")
    table.add_column("Minute", style="dim")
    
    with _dashboard_lock:
        if not _fixture_stats:
            table.add_row("—", "—", "—", "—", "—", "Waiting...", "—")
            return table
        
        for fixture_id, data in sorted(_fixture_stats.items()):
            if not data['conditions']:
                continue
            
            for stat_name, team_name, target in data['conditions']:
                key = f"{team_name}_{stat_name}"
                current = data['current_values'].get(key, "—")
                cond_key = (stat_name, team_name, target)
                minute_met = data['met_conditions'].get(cond_key)
                match_finished = data['match_finished']
                
                # Determine status and minute display
                if data['alert_triggered']:
                    # Alert was triggered - show ALERT status
                    status = "✅ ALERT"
                    status_style = "green"
                    # Show the minute when this condition was met
                    if minute_met is not None:
                        minute_str = f"{minute_met}'"
                    else:
                        minute_str = f"{data['alert_minute']}'" if data['alert_minute'] else "—"
                elif minute_met is not None:
                    # Condition was met but alert not yet triggered (waiting for other conditions)
                    status = "🎯 MET"
                    status_style = "yellow"
                    minute_str = f"{minute_met}'"
                elif match_finished:
                    # Match finished and condition was never met
                    status = "❌ Unmet"
                    status_style = "red"
                    minute_str = "90'"  # Show 90' for unmet conditions at match end
                else:
                    # Match still in progress, tracking the condition
                    progress = ""
                    if current != "—" and target > 0:
                        try:
                            pct = min(100, int((int(current) / target) * 100))
                            progress = f" ({pct}%)"
                        except (ValueError, TypeError):
                            pass
                    status = f"⏳ Tracking{progress}"
                    status_style = "cyan"
                    minute_str = f"{data['elapsed_minute']}'" if data['elapsed_minute'] else "—"
                
                table.add_row(
                    str(fixture_id),
                    stat_name,
                    team_name,
                    str(current),
                    str(target),
                    Text(status, style=status_style),
                    minute_str
                )
    
    return table


def _build_alerts_panel():
    """Build the alerts summary panel."""
    with _dashboard_lock:
        total_alerts = _global_stats['total_alerts']
        triggered_count = sum(1 for data in _fixture_stats.values() if data['alert_triggered'])
        fixtures = _global_stats['fixtures_count']
        
        elapsed = (datetime.now() - _global_stats['start_time']).total_seconds()
        elapsed_str = f"{int(elapsed // 60)}m {int(elapsed % 60)}s"
        
        # Determine status based on monitoring flag
        if _global_stats['monitoring']:
            status_text = "🟢 Monitoring Active"
            status_style = "green"
        else:
            status_text = "🔴 Monitoring Finished"
            status_style = "red"
        
        alert_text = f"""
[bold cyan]Alerts Triggered:[/bold cyan] [green]{total_alerts}[/green]
[bold cyan]Fixtures Monitored:[/bold cyan] [magenta]{fixtures}[/magenta]
[bold cyan]Conditions Met:[/bold cyan] [yellow]{triggered_count}[/yellow]
[bold cyan]Elapsed Time:[/bold cyan] [blue]{elapsed_str}[/blue]
[bold cyan]Status:[/bold cyan] [{status_style}]{status_text}[/{status_style}]
"""
    
    return Panel(alert_text.strip(), title="📈 Summary", border_style="cyan")


def _build_dashboard():
    """Build the complete dashboard layout."""
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body"),
        Layout(name="footer", size=3)
    )
    
    # Header
    title = Text("⚽ Football Alert CLI - Live Dashboard", style="bold white")
    layout["header"].update(Panel(Align.center(title), style="bold blue"))
    
    # Body: split into stats table and alerts
    layout["body"].split_row(
        Layout(name="stats"),
        Layout(name="alerts", size=30)
    )
    
    layout["body"]["stats"].update(_build_stats_table())
    layout["body"]["alerts"].update(_build_alerts_panel())
    
    # Footer
    footer_text = Text("Press Ctrl+C to stop monitoring", style="dim white")
    layout["footer"].update(Panel(Align.center(footer_text), style="dim"))
    
    return layout


def run_dashboard_live():
    """
    Run the live-updating dashboard using Rich's Live display.
    This should be called in the main thread before starting monitoring threads.
    """
    console = Console()
    
    try:
        with Live(_build_dashboard(), refresh_per_second=2, console=console) as live:
            # Keep the dashboard running while monitoring is active
            while _global_stats['monitoring']:
                live.update(_build_dashboard())
                time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        stop_monitoring()


def start_dashboard_thread():
    """
    Start the dashboard in a background thread.
    Returns the thread object for joining if needed.
    """
    dashboard_thread = threading.Thread(target=run_dashboard_live, daemon=False)
    dashboard_thread.start()
    return dashboard_thread


def show_history():
    """Display the session history using Rich."""
    import json
    import os
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel

    console = Console()
    history_file = "history.json"

    if not os.path.exists(history_file):
        console.print("[yellow]No history found.[/yellow]")
        return

    try:
        with open(history_file, "r") as f:
            history = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        console.print(f"[red]Error reading history: {e}[/red]")
        return

    if not history:
        console.print("[yellow]History is empty.[/yellow]")
        return

    console.print(Panel(Align.center(Text("📜 Football Alert History", style="bold white")), style="bold blue"))

    for i, session in enumerate(reversed(history), 1):
        timestamp = session.get("timestamp", "Unknown")
        dt = datetime.fromisoformat(timestamp).strftime("%Y-%m-%d %H:%M:%S")
        
        table = Table(title=f"Session {i} - {dt}", show_header=True, header_style="bold cyan", expand=True)
        table.add_column("Fixture ID", style="magenta")
        table.add_column("Status", style="white")
        table.add_column("Conditions", style="cyan")
        table.add_column("Final Stats", style="yellow")
        table.add_column("Alert Minute", style="dim")

        for fixture in session.get("fixtures", []):
            fid = fixture.get("fixture_id", "Unknown")
            status = fixture.get("status", "Unknown")
            
            # Format conditions
            cond_list = []
            for c in fixture.get("conditions", []):
                cond_list.append(f"{c['team']} {c['stat']} >= {c['target']}")
            conds_str = "\n".join(cond_list)

            # Format final stats
            stats_list = []
            for k, v in fixture.get("final_stats", {}).items():
                stats_list.append(f"{k}: {v}")
            stats_str = "\n".join(stats_list) if stats_list else "—"

            alert_min = fixture.get("alert_minute")
            alert_min_str = f"{alert_min}'" if alert_min else "—"

            status_style = "white"
            if status == "Alert Triggered":
                status_style = "green"
            elif status == "Finished":
                status_style = "blue"
            elif status == "Stopped":
                status_style = "yellow"

            table.add_row(
                str(fid),
                Text(status, style=status_style),
                conds_str,
                stats_str,
                alert_min_str
            )
        
        console.print(table)
        console.print("\n")
