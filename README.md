Markdown
# Football Alert CLI

A professional Python CLI application for tracking live football match statistics using a local mock server (no external network deps). Set targets for statistics (e.g., corners reach 5 for a team), and receive an alert once reached or exceeded. No logical operators required.

Supports multiple matches tracked simultaneously. For multiple statistics per match/fixture, alerts trigger ONLY when ALL specified conditions are met simultaneously (AND logic). Now includes the match minute when all statistics reach their threshold values. Cumulative mock data ensures reliable triggering for complex cases (no infinite loops).

## Setup

For Linux/Debian-based environments (common in containers/test setups) missing pip/venv, first bootstrap:

```bash
# Install system packages (no sudo if root; run once)
apt-get update -qq && apt-get install -y python3-pip python3-venv
```

1. (Re)create clean venv:
   ```bash
   rm -rf venv
   python3 -m venv venv
   ```

2. Activate the environment:
   ```bash
   # Windows (PowerShell)
   .\venv\Scripts\activate
   # Mac/Linux
   source venv/bin/activate
   ```

3. Install the package (editable mode):
   ```bash
   pip install -e .
   ```
   (Installs Click and requests; mock server uses Python stdlib. Re-run this after code changes.)

**No external API key required!** The project now uses a local mock server by default to comply with restrictions on external network dependencies (e.g., no RapidAPI calls). 

- CLI entrypoint `football-alert` available post-install/activation (try examples below).
- `--mock` flag for fast in-memory sim (still needs Click; supports new minute-in-match alerts).
- All stats simulated locally; fixture IDs accepted for compatibility.
- Mock server runs automatically on localhost:5000 when needed (stdlib-only).

## Local Mock Server

To comply with no external network dependencies:
- A stdlib-based mock server (`http.server`) is included in `football_alert/mock_server.py`.
- It mimics the original RapidAPI endpoint at `http://127.0.0.1:5000/fixtures/statistics`.
- Stats (Corners, Shots, Goals) are dynamically simulated and change over time for realistic monitoring demos (incl. elapsed minute field for reporting when thresholds reached).
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
Track different stats simultaneously in the same fixture. Alert triggers ONLY when ALL conditions met (e.g., Corners AND Total Shots); uses the EXACT new professional format:
```bash
football-alert alert \
  --fixture-id 123456 --stat Corners --team "Home Team" --target 3 \
  --fixture-id 123456 --stat "Total Shots" --team "Away Team" --target 5 \
  --mock --interval 1
```
(Example output: "🚨 ALERT: Home Team reached 3 Corners. (15'); Away Team reached 5 Total Shots. (15')")

**Multiple Matches Tracked Simultaneously**
Monitor stats across several fixtures in *parallel* (each in independent thread; non-blocking, no synchronous loop issues; fixed key consistency for reliable triggering in mixed modes):
```bash
# Multi-fixture test command (with multi-stat per fixture for full concurrency demo)
# Uses small targets/short interval + --mock for quick alerts
# Now reliably triggers all (e.g., no stuck loops after first alert)
# Each fixture's alert follows exact new format
football-alert alert \
  --fixture-id 123 --stat Corners --team "Home Team" --target 1 \
  --fixture-id 123 --stat "Total Shots" --team "Away Team" --target 2 \
  --fixture-id 456 --stat Goals --team "Home Team" --target 1 \
  --fixture-id 456 --stat Corners --team "Away Team" --target 1 \
  --mock --interval 1
```

Fixture IDs are placeholders (from original API docs at https://www.api-football.com/); simulation ignores them for demo purposes. Use small targets/short intervals in --mock to see alerts quickly (minute advances ~5 per poll). Cumulative stats (with type-normalized keys) ensure multi-stat/multi-match cases trigger reliably without loops. 

Example concurrent output (new format; one line per fixture):
- "🚨 ALERT: Home Team reached 1 Corners. (5'); Away Team reached 2 Total Shots. (5')"
- "🚨 ALERT: Home Team reached 1 Goals. (10'); Away Team reached 1 Corners. (10')" (in parallel)

**Live Terminal Dashboard (Rich UI)**
Monitor matches with a professional live-updating terminal dashboard powered by the Rich library. Use the `--dashboard` flag to enable it:
```bash
football-alert alert \
  --fixture-id 123 --stat Corners --team "Home Team" --target 3 \
  --fixture-id 123 --stat "Total Shots" --team "Away Team" --target 5 \
  --mock --interval 1 --dashboard
```

The dashboard displays:
- **Live Match Statistics Table**: Shows all tracked conditions with real-time updates
  - Fixture ID, Statistic name, Team, Current value, Target value, Progress status
  - Status indicators: ⏳ Tracking (with %), 🎯 MET (threshold reached), ✅ ALERT (triggered)
  - Match minute when threshold was reached
- **Summary Panel**: Key metrics including alerts triggered, fixtures monitored, elapsed time, and monitoring status
- **Real-time Updates**: Dashboard refreshes 2x per second to reflect live data
- **Professional UI**: Color-coded output with emojis for easy scanning

The dashboard is completely optional—omit `--dashboard` to use the original console output with alerts.
## Features

- **Local Mock Server**: Fully replaces RapidAPI to enforce no external network dependencies. Implemented with Python stdlib (`http.server`) only - no extra packages. Cumulative stats (with fixture ID type normalization for str/int consistency) prevent loops in multi-stat/multi-match cases. Now simulates elapsed minute (~5 min per poll, capped at 90) for realistic timing.
- **Live Terminal Dashboard**: Professional Rich-powered UI for real-time monitoring with color-coded status indicators, progress tracking, and summary metrics. Optional `--dashboard` flag enables live-updating terminal visualization.
- Tracks stats like Corners, Total Shots, Goals, etc., for home/away teams.
- **Concurrent multi-match support**: Fixtures monitored in independent threads (non-blocking, true parallelism; fixed for reliable alerts across all fixtures).
- **Multi-stat per match**: Alerts trigger ONLY when ALL conditions met simultaneously (AND logic for stats in same fixture; independent per fixture). Uses exact new format (e.g., "[Team] reached [Target] [Stat]. ([Min]'); ...").
- Alerts fire when stat reaches/exceeds target (simple, operator-free) with professional formatting (e.g., "🚨 ALERT: Home Team reached 3 Corners. (15'); Away Team reached 5 Total Shots. (15')").
- Mock mode (`--mock`) for in-memory testing; extendable for notifications (e.g., email).

## Development & Testing

- Reinstall after changes: `pip install -e .` (if using editable install).
- Run CLI examples above (no API key or internet needed; mock server handles all).
- Test server standalone: `python -m football_alert.mock_server` (Ctrl+C to stop; pure stdlib).
- To verify mock endpoint (using stdlib): `python3 -c "import urllib.request, json; d=json.loads(urllib.request.urlopen('http://127.0.0.1:5000/fixtures/statistics?fixture=123').read()); print(d)"` (should return JSON stats with 'elapsed' minute field for threshold timing).
- Test complex multi-match/multi-stat: Use examples with --mock (cumulative data ensures no stuck loops; check exact new alert format e.g., "🚨 ALERT: Home Team reached 1 Corners. (5'); ...").
- (Note: pytest tests/ mentioned in original but directory may need setup for full coverage; core tested via manual runs.)

Since the test environment may lack pip/venv, direct Python module testing is used internally.

## Project Structure

- `football_alert/mock_server.py`: Local API mock using only Python stdlib (`http.server`, `threading`, etc.) - no third-party libs. Cumulative stats (fixture_id normalized to str) + elapsed minute for reliable multi-stat/multi-match triggering and "when" (minute) reporting.
- `football_alert/api.py`: Updated to use local server exclusively for network compliance (retains requests for local calls); in-memory mock also cumulative and now returns (stats, elapsed) tuple.
- `football_alert/monitor.py`: Core monitoring refactored for concurrent threads per fixture (independent, non-blocking); alerts now include match minute when all stats thresholds reached. Integrates with dashboard for optional live UI.
- `football_alert/dashboard.py`: **NEW** Live-updating Rich terminal UI module. Displays real-time statistics, progress tracking, alerts, and monitoring summary. Thread-safe state management for concurrent fixture updates. Optional feature activated via `--dashboard` CLI flag.
- `football_alert/cli.py`: CLI entrypoint (backward compatible, updated docs for concurrency/multi-stat). Now includes `--dashboard` flag for Rich UI.
- `setup.py`: Updated dependencies to include Rich library for dashboard visualization.

Code is clean, type-hinted where applicable, and modular.

For issues or extensions (e.g., real notifications), refer to the source files.