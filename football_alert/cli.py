import click
from .monitor import start_monitoring
from .mock_server import get_mock_fixtures

STAT_OPTIONS = ["Corners", "Total Shots", "Goals"]


def _prompt_fixture_choice(fixtures):
    """Prompt user to select a fixture from the mock list."""
    choices = [
        click.Choice([str(fixture["fixture_id"]) for fixture in fixtures], case_sensitive=False)
    ]
    fixture_lookup = {str(fixture["fixture_id"]): fixture for fixture in fixtures}
    fixture_id = click.prompt(
        "Select fixture ID",
        type=choices[0]
    )
    return fixture_lookup[str(fixture_id)]


def _prompt_conditions(fixture, count):
    """Prompt user to select stat/team/target combos for a fixture."""
    conditions = []
    team_choices = [fixture["home_team"], fixture["away_team"]]
    for idx in range(count):
        stat_choice = click.prompt(
            f"Select statistic #{idx + 1}",
            type=click.Choice(STAT_OPTIONS, case_sensitive=False)
        )
        team_choice = click.prompt(
            f"Select team for {stat_choice}",
            type=click.Choice(team_choices, case_sensitive=False)
        )
        target_choice = click.prompt(
            f"Target value for {stat_choice}",
            type=click.IntRange(1, 99)
        )
        conditions.append({
            "fixture_id": fixture["fixture_id"],
            "stat": stat_choice,
            "team": team_choice,
            "target": target_choice
        })
    return conditions


def _interactive_config():
    """Build monitoring configs via interactive prompts using mock fixtures."""
    fixtures = get_mock_fixtures()
    if not fixtures:
        click.echo("No mock fixtures available.")
        return []

    click.echo("\nAvailable Mock Fixtures:")
    for fixture in fixtures:
        click.echo(f"- {fixture['fixture_id']}: {fixture['home_team']} vs {fixture['away_team']}")

    fixture_count = click.prompt(
        "How many fixtures would you like to monitor?",
        type=click.IntRange(1, len(fixtures)),
        default=1
    )

    configs = []
    selected_fixture_ids = set()
    for _ in range(fixture_count):
        fixture = _prompt_fixture_choice(fixtures)
        while fixture["fixture_id"] in selected_fixture_ids:
            click.echo("Fixture already selected; choose a different match.")
            fixture = _prompt_fixture_choice(fixtures)
        selected_fixture_ids.add(fixture["fixture_id"])

        stat_count = click.prompt(
            f"How many stats to track for {fixture['home_team']} vs {fixture['away_team']}?",
            type=click.IntRange(1, 3),
            default=1
        )
        configs.extend(_prompt_conditions(fixture, stat_count))

    return configs

@click.group()
def main():
    """Football Alert CLI Tool."""
    pass

@main.command()
@click.option('--fixture-id', multiple=True, required=False, type=int, help='ID of the football match (can be used multiple times).')
@click.option('--stat', multiple=True, required=False, type=str, help='Statistic to track (e.g., Corners).')
@click.option('--team', multiple=True, required=False, type=str, help='Team name (Home Team or Away Team).')
@click.option('--target', multiple=True, required=False, type=int, help='Target number for the statistic.')
@click.option('--interval', default=60, help='Polling interval in seconds.')
@click.option('--mock', is_flag=True, help='Use mock data for testing.')
@click.option('--dashboard', is_flag=True, help='Enable live-updating Rich terminal dashboard.')
@click.option('--interactive', is_flag=True, help='Use mock fixtures and select match/stat/target via prompts.')
def alert(fixture_id, stat, team, target, interval, mock, dashboard, interactive):
    """
    Track matches and send alerts.
    Inputs must be paired (same number of --fixture-id, --stat, --team, --target).
    For multiple stats on the same fixture-id, alerts trigger ONLY when ALL are met (AND logic).
    Fixtures are monitored concurrently in threads (independent, non-blocking).
    Ctrl+C gracefully stops all.
    Use --dashboard to display a live-updating terminal UI powered by Rich library.
    Use --interactive to select from mock fixtures and prompt for match/stat/target.
    """
    if interactive:
        if fixture_id or stat or team or target:
            click.echo("Error: --interactive cannot be combined with manual --fixture-id/--stat/--team/--target options.")
            return
        mock = True
        configs = _interactive_config()
        if not configs:
            click.echo("No selections made. Exiting.")
            return
        start_monitoring(configs, interval, mock, use_dashboard=dashboard)
        return

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