# Shadow Queen v1.1 — Stability + Integrity

Hardening branch.

## New

- three-phase verification
  - good
  - bad
  - inversed
  - remirrored
- config SHA256 integrity record
- tamper heartbeat state
- SQLite integrity check
- daemon retained
- rotating logs retained

## Run

```bash
python selftest.py
python -m shadowqueen.cli scan phase_events.json
python -m shadowqueen.cli daemon --config config.example.json
python -m shadowqueen.cli --db shadowqueen.db stats
```

## Three-phase rule

```text
direct check
inverse mirror check
re-mirror stability check
```

Good/remirrored-good may pass. Bad/inversed quarantines.
