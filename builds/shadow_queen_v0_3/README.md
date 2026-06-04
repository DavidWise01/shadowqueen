# Shadow Queen v0.3

Live streaming telemetry prototype.

## New

- JSONL stream mode
- `--live` follow mode for appended JSONL
- batch stream catch-up
- basic interval collector
- recent stats
- continuous SQLite persistence

## Run

```bash
python selftest.py
python -m shadowqueen.cli --db demo.db demo
python -m shadowqueen.cli --db demo.db scan sample_events.json
python -m shadowqueen.cli --db demo.db stream sample_stream.jsonl
python -m shadowqueen.cli --db demo.db stream sample_stream.jsonl --live --stop-after 10
python -m shadowqueen.cli --db demo.db collect --interval 2 --duration 10
python -m shadowqueen.cli --db demo.db stats --recent 10
```

Still not production: no kernel hooks, packet capture, eBPF, model-weight inspection, or enforcement driver.
