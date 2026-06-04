# Shadow Queen v0.2

Persistent local prototype for the Shadow Queen AI immune/anomaly engine.

## New in v0.2

- SQLite persistent memory
- persistent fingerprint memory
- persistent lineage risk
- scan JSON/JSONL
- basic collector command
- stats command

## Run

```bash
python selftest.py
python -m shadowqueen.cli --db demo.db demo
python -m shadowqueen.cli --db demo.db scan sample_events.json
python -m shadowqueen.cli --db demo.db collect
python -m shadowqueen.cli --db demo.db stats
```

Still not production: no kernel hooks, no packet capture, no malware corpus, no sandbox enforcement.
