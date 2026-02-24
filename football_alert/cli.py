import click
from .monitor import start_monitoring

@click.group()
def main():
    """Football Alert CLI Tool."""
    pass

@main.command()
@click.option('--fixture-id', multiple=True, required=True, type=int, help='ID of the football match (can be used multiple times).')
@click.option('--stat', multiple=True, required=True, type=str, help='Statistic to track (e.g., Corners).')
@click.option('--team', multiple=True, required=True, type=str, help='Team name (Home Team or Away Team).')
@click.option('--target', multiple=True, required=True, type=int, help='Target number for the statistic.')
@click.option('--interval', default=60, help='Polling interval in seconds.')
@click.option('--mock', is_flag=True, help='Use mock data for testing.')
@click.option('--dashboard', is_flag=True, help='Enable live-updating Rich terminal dashboard.')
def alert(fixture_id, stat, team, target, interval, mock, dashboard):
    """
    Track matches and send alerts.
    Inputs must be paired (same number of --fixture-id, --stat, --team, --target).
    For multiple stats on the same fixture-id, alerts trigger ONLY when ALL are met (AND logic).
    Fixtures are monitored concurrently in threads (independent, non-blocking).
    Ctrl+C gracefully stops all.
    Use --dashboard to display a live-updating terminal UI powered by Rich library.
    """
    # Validation: Ensure all lists have the same length
    if not (len(fixture_id) == len(stat) == len(team) == len(target)):
        click.echo("Error: You must provide equal numbers of --fixture-id, --stat, --team, and --target arguments.")
        return

    # Prepare configurations
    configs = []
    for i in range(len(fixture_id)):
        configs.append({
            'fixture_id': fixture_id[i],
            'stat': stat[i],
            'team': team[i],
            'target': target[i]
        })

    start_monitoring(configs, interval, mock, use_dashboard=dashboard)

if __name__ == '__main__':
    main()