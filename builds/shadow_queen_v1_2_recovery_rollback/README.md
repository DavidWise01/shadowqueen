# Shadow Queen v1.2 — Recovery + Rollback

Adds checkpoint, restore, and evidence bundle support.

## New

- snapshot table
- recovery actions table
- DB backup checkpoint
- config backup checkpoint
- restore command
- evidence bundle export
- checkpoint-on-quarantine support
- daemon checkpoint-on-start support

## Run

```bash
python selftest.py
python -m shadowqueen.cli --db sq.db checkpoint clean --config config.example.json
python -m shadowqueen.cli --db sq.db scan phase_events.json --checkpoint-on-quarantine --config config.example.json
python -m shadowqueen.cli --db sq.db evidence evidence.zip
python -m shadowqueen.cli --db sq.db restore --label clean
python -m shadowqueen.cli daemon --config config.example.json
python -m shadowqueen.cli --db shadowqueen.db stats
```

Rollback is conservative: it copies backups and never deletes originals.
