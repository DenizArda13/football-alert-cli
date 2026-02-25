"""
Interactive fixture generator for Football Alert CLI.
Allows users to select matches, statistics, and target values through a UI.
"""

import click
from .mock_server import get_fixtures, get_available_stats


def display_fixtures():
    """Display available fixtures in a formatted table."""
    fixtures = get_fixtures()
    click.echo("\n" + "=" * 90)
    click.echo("⚽ Available Matches:")
    click.echo("=" * 90)
    
    for idx, fixture in enumerate(fixtures, 1):
        click.echo(
            f"{idx}. [{fixture['id']}] {fixture['home_team']} vs {fixture['away_team']} "
            f"({fixture['league']})"
        )
    
    click.echo("=" * 90 + "\n")
    return fixtures


def select_fixture():
    """Interactive fixture selection."""
    fixtures = display_fixtures()
    
    while True:
        try:
            choice = click.prompt(
                "Select a match (enter number)",
                type=int,
                default=1
            )
            if 1 <= choice <= len(fixtures):
                selected = fixtures[choice - 1]
                click.echo(f"\n✓ Selected: {selected['home_team']} vs {selected['away_team']}")
                return selected
            else:
                click.echo(f"❌ Please enter a number between 1 and {len(fixtures)}")
        except ValueError:
            click.echo("❌ Invalid input. Please enter a valid number.")


def display_teams_and_stats(fixture):
    """Display teams and available statistics."""
    stats = get_available_stats()
    
    click.echo("\n" + "=" * 90)
    click.echo("📊 Available Statistics:")
    click.echo("=" * 90)
    
    for idx, stat in enumerate(stats, 1):
        click.echo(f"{idx}. {stat}")
    
    click.echo("\n" + "=" * 90)
    click.echo("👥 Teams:")
    click.echo("=" * 90)
    click.echo(f"1. {fixture['home_team']} (Home)")
    click.echo(f"2. {fixture['away_team']} (Away)")
    click.echo("=" * 90 + "\n")
    
    return stats


def select_statistic():
    """Interactive statistic selection."""
    stats = get_available_stats()
    
    while True:
        try:
            choice = click.prompt(
                "Select a statistic (enter number)",
                type=int,
                default=1
            )
            if 1 <= choice <= len(stats):
                selected = stats[choice - 1]
                click.echo(f"✓ Selected statistic: {selected}")
                return selected
            else:
                click.echo(f"❌ Please enter a number between 1 and {len(stats)}")
        except ValueError:
            click.echo("❌ Invalid input. Please enter a valid number.")


def select_team(fixture):
    """Interactive team selection."""
    teams = [
        {"name": fixture['home_team'], "type": "Home"},
        {"name": fixture['away_team'], "type": "Away"}
    ]
    
    while True:
        try:
            choice = click.prompt(
                "Select a team (enter number)",
                type=int,
                default=1
            )
            if 1 <= choice <= len(teams):
                selected = teams[choice - 1]
                click.echo(f"✓ Selected team: {selected['name']} ({selected['type']})")
                return selected['name']
            else:
                click.echo(f"❌ Please enter a number between 1 and {len(teams)}")
        except ValueError:
            click.echo("❌ Invalid input. Please enter a valid number.")


def select_target_value():
    """Interactive target value selection."""
    click.echo("\nEnter the target value for this statistic.")
    click.echo("Examples: Corners (3-5), Shots (5-10), Goals (1-3)")
    
    while True:
        try:
            target = click.prompt(
                "Target value",
                type=int,
                default=3
            )
            if target > 0:
                click.echo(f"✓ Target value set to: {target}")
                return target
            else:
                click.echo("❌ Target value must be greater than 0")
        except ValueError:
            click.echo("❌ Invalid input. Please enter a valid number.")


def add_another_condition():
    """Ask if user wants to add another condition for the same fixture."""
    response = click.confirm(
        "\nAdd another statistic for this match?",
        default=False
    )
    return response


def interactive_fixture_setup():
    """
    Main interactive fixture setup workflow.
    Returns a list of configuration dicts ready for monitoring.
    """
    click.echo("\n" + "=" * 90)
    click.echo("🎯 Football Alert - Interactive Fixture Setup")
    click.echo("=" * 90)
    
    configs = []
    
    # Select fixture
    fixture = select_fixture()
    
    # Allow multiple statistics for same fixture
    while True:
        # Display available options
        display_teams_and_stats(fixture)
        
        # Select statistic
        stat = select_statistic()
        
        # Select team
        team = select_team(fixture)
        
        # Select target value
        target = select_target_value()
        
        # Add to configs
        config = {
            'fixture_id': fixture['id'],
            'stat': stat,
            'team': team,
            'target': target
        }
        configs.append(config)
        
        click.echo(f"\n✓ Condition added: {team} - {stat} >= {target}")
        
        # Ask if user wants to add another condition
        if not add_another_condition():
            break
    
    # Summary
    click.echo("\n" + "=" * 90)
    click.echo("📋 Configuration Summary:")
    click.echo("=" * 90)
    click.echo(f"Match: {fixture['home_team']} vs {fixture['away_team']}")
    click.echo(f"Fixture ID: {fixture['id']}")
    click.echo("Conditions:")
    for i, config in enumerate(configs, 1):
        click.echo(f"  {i}. {config['team']} - {config['stat']} >= {config['target']}")
    click.echo("=" * 90 + "\n")
    
    return configs
