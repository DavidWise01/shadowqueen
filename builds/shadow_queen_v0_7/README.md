# Shadow Queen v0.7 — Alert Engine

## New

- SQLite alerts table
- severity mapping
- recommended actions
- alerts CLI
- JSON report export

## Run

```bash
python selftest.py
python -m shadowqueen.cli --db sq.db scan alert_events.json
python -m shadowqueen.cli --db sq.db stats
python -m shadowqueen.cli --db sq.db alerts --limit 10
python -m shadowqueen.cli --db sq.db alerts --severity critical
python -m shadowqueen.cli --db sq.db report report.json
```
