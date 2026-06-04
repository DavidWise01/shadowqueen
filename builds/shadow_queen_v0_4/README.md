# Shadow Queen v0.4

Safe user-space collectors.

## New

- process snapshot collector
- file snapshot collector
- network connection snapshot
- SQLite persistence

## Run

```bash
python selftest.py
python -m shadowqueen.cli --db sq.db scan sample_events.json
python -m shadowqueen.cli --db sq.db collect --process --network
python -m shadowqueen.cli --db sq.db collect --files /tmp --recursive --limit 100
python -m shadowqueen.cli --db sq.db stats --recent 10
```

Still user-space observation only: no kernel hooks, packet sniffing, or enforcement driver.
