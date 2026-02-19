Markdown
# Football Alert CLI

A professional Python CLI application for tracking live football match statistics using a local mock server (no external network deps). Set targets for statistics (e.g., corners reach 5 for a team), and receive an alert once reached or exceeded. No logical operators required.

Supports multiple matches tracked simultaneously. For multiple statistics per match/fixture, alerts trigger ONLY when ALL specified conditions are met simultaneously (AND logic). Cumulative mock data ensures reliable triggering for complex cases (no infinite loops).

## Setup

1. Activate the environment:
   ```bash
   # Windows (PowerShell)
   .\venv\Scripts\activate
   # Mac/Linux
   source venv/bin/activate
   ```
2. Install the package (editable mode):
   ```bash
   pip install -e .
   ```
   (Only Click and requests are required; mock server uses Python stdlib.)

**No external API key required!** The project now uses a local mock server by default to comply with restrictions on external network dependencies (e.g., no RapidAPI calls). 

- The mock server runs automatically on localhost:5000 when needed.
- Original `--mock` flag still supported for in-memory simulation (faster, no server).
- All stats are simulated locally; fixture IDs are ignored in mocks but accepted for compatibility.

## Local Mock Server

To comply with no external network dependencies:
- A stdlib-based mock server (`http.server`) is included in `football_alert/mock_server.py`.
- It mimics the original RapidAPI endpoint at `http://127.0.0.1:5000/fixtures/statistics`.
- Stats (Corners, Shots, Goals) are dynamically simulated and change over time for realistic monitoring demos.
- Server starts automatically on first API call (in background thread); no manual intervention or extra libs needed.
- You can run it standalone: `python -m football_alert.mock_server` (uses only standard library).

## Usage Examples

The `--mock` flag uses fast in-memory simulation; omit it to use the HTTP local mock server (still no external calls).

**Single Match and Statistic**
```bash
football-alert alert --fixture-id 123456 --stat Corners --team "Home Team" --target 5 --interval 1
```
(Note: `--mock` optional; fixture ID accepted for compatibility but not used in simulation.)

**Multiple Statistics for One Match**
Track different stats simultaneously in the same fixture. Alert triggers ONLY when ALL conditions met (e.g., Corners AND Total Shots); uses professional format:
```bash
football-alert alert \
  --fixture-id 123456 --stat Corners --team "Home Team" --target 3 \
  --fixture-id 123456 --stat "Total Shots" --team "Away Team" --target 5 \
  --mock --interval 1
```
(Example output: "🚨 ALERT: Fixture 123456 - Targets reached: Home Team reached 5 corners; Away Team reached 6 total shots.")

**Multiple Matches Tracked Simultaneously**
Monitor stats across several fixtures in *parallel* (each in independent thread; non-blocking, no synchronous loop issues):
```bash
# Multi-fixture test command (with multi-stat per fixture for full concurrency demo)
# Uses small targets/short interval + --mock for quick alerts
football-alert alert \
  --fixture-id 123 --stat Corners --team "Home Team" --target 1 \
  --fixture-id 123 --stat "Total Shots" --team "Away Team" --target 2 \
  --fixture-id 456 --stat Goals --team "Home Team" --target 1 \
  --fixture-id 456 --stat Corners --team "Away Team" --target 1 \
  --mock --interval 1
```

Fixture IDs are placeholders (from original API docs at https://www.api-football.com/); simulation ignores them for demo purposes. Use small targets/short intervals in --mock to see alerts quickly. Cumulative stats ensure multi-stat cases trigger reliably. 

Example concurrent output:
- "🚨 ALERT: Fixture 123 - Targets reached: ..."
- "🚨 ALERT: Fixture 456 - Targets reached: ..." (in parallel)
## Features

- **Local Mock Server**: Fully replaces RapidAPI to enforce no external network dependencies. Implemented with Python stdlib (`http.server`) only - no extra packages. Cumulative stats prevent loops in multi-stat cases.
- Tracks stats like Corners, Total Shots, Goals, etc., for home/away teams.
- **Concurrent multi-match support**: Fixtures monitored in independent threads (non-blocking, true parallelism).
- **Multi-stat per match**: Alerts trigger ONLY when ALL conditions met simultaneously (AND logic for stats in same fixture; independent per fixture).
- Alerts fire when stat reaches/exceeds target (simple, operator-free) with professional formatting (e.g., "🚨 ALERT: Fixture X - Targets reached: ...").
- Mock mode (`--mock`) for in-memory testing; extendable for notifications (e.g., email).

## Development & Testing

- Reinstall after changes: `pip install -e .` (if using editable install).
- Run CLI examples above (no API key or internet needed; mock server handles all).
- Test server standalone: `python -m football_alert.mock_server` (Ctrl+C to stop; pure stdlib).
- To verify mock endpoint (using stdlib): `python3 -c "import urllib.request, json; d=json.loads(urllib.request.urlopen('http://127.0.0.1:5000/fixtures/statistics?fixture=123').read()); print(d)"` (should return JSON stats).
- Test complex multi-match/multi-stat: Use examples with --mock (cumulative data ensures no stuck loops; check professional alerts).
- (Note: pytest tests/ mentioned in original but directory may need setup for full coverage; core tested via manual runs.)

Since the test environment may lack pip/venv, direct Python module testing is used internally.

## Project Structure

- `football_alert/mock_server.py`: Local API mock using only Python stdlib (`http.server`, `threading`, etc.) - no third-party libs. Cumulative stats for reliable multi-stat triggering.
- `football_alert/api.py`: Updated to use local server exclusively for network compliance (retains requests for local calls); in-memory mock also cumulative.
- `football_alert/monitor.py`: Core monitoring refactored for concurrent threads per fixture (independent, non-blocking).
- `football_alert/cli.py`: CLI entrypoint (backward compatible, updated docs for concurrency/multi-stat).
- `setup.py`: No additional deps beyond original.

Code is clean, type-hinted where applicable, and modular.

For issues or extensions (e.g., real notifications), refer to the source files.