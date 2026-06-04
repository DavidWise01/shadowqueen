# Shadow Queen v0.8 — Baseline Learning

Learns normal source/type patterns, then alerts on drift.

## New

- baselines table
- learn mode
- baseline drift scoring
- low-confidence vs new-source drift
- baselines CLI

## Run

```bash
python selftest.py
python -m shadowqueen.cli --db sq.db scan train_events.json --learn
python -m shadowqueen.cli --db sq.db scan test_events.json
python -m shadowqueen.cli --db sq.db stats
python -m shadowqueen.cli --db sq.db baselines
python -m shadowqueen.cli --db sq.db alerts
```
