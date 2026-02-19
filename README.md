Markdown
# Football Alert CLI

A professional Python CLI application for tracking live football match statistics. Set targets for statistics (e.g., corners reach 5 for a team), and receive an alert once reached or exceeded. No logical operators required.

Supports multiple matches tracked simultaneously and multiple statistics per match.

## Setup

1. Activate the environment:
   ```bash
   # Windows (PowerShell)
   .\venv\Scripts\activate
   # Mac/Linux
   source venv/bin/activate
Install the package (editable mode):

Bash
pip install -e .
For real data (optional): Obtain a free API key from API-Football (RapidAPI) and export it:

Bash
# Linux/Mac
export FOOTBALL_API_KEY=your_api_key_here
# Windows (PowerShell)
$env:FOOTBALL_API_KEY="your_api_key_here"
Free tier available (rate-limited). Use --mock for testing without a key.

Usage Examples
Fixture IDs can be found in the API documentation at https://www.api-football.com/.

Single Match and Statistic
Bash
football-alert alert --fixture-id 123456 --stat Corners --team "Home Team" --target 5 --mock --interval 1
Multiple Statistics for One Match
Track different stats simultaneously in the same fixture:

Bash
football-alert alert \
  --fixture-id 123456 --stat Corners --team "Home Team" --target 3 \
  --fixture-id 123456 --stat "Total Shots" --team "Away Team" --target 5 \
  --mock --interval 1
Multiple Matches Tracked Simultaneously
Monitor stats across several fixtures in parallel:

Bash
football-alert alert \
  --fixture-id 123 --stat Corners --team "Home Team" --target 3 \
  --fixture-id 456 --stat "Total Shots" --team "Away Team" --target 4 \
  --mock --interval 1
Features
Tracks stats like Corners, Total Shots, Goals, etc., for home/away teams.

Simultaneous multi-match support: Efficient polling across fixtures.

Multi-stat per match: Independent alerts for different conditions.

Alerts fire when stat reaches/exceeds target (simple, operator-free).

Professional, concise alert messages.

Mock mode for testing; extendable for notifications (e.g., email).

Development & Testing
Run tests: python -m pytest tests/ -q (covers core logic, multi-scenarios).

Structure: API wrapper (api.py), monitoring (monitor.py), CLI (cli.py with Click).

Code is clean, type-hinted, and modular for final delivery.

For issues or extensions, refer to the source files.