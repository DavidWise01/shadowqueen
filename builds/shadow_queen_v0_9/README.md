# Shadow Queen v0.9 — Safe Policy Actions

## New

- policy action audit table
- denylist
- watchlist
- audit mode vs apply mode
- safe quarantine-copy for files
- no deletion, no process killing, no firewall changes

## Run

```bash
python selftest.py
python -m shadowqueen.cli --db sq.db scan train_events.json --learn
python -m shadowqueen.cli --db sq.db scan policy_events.json --policy-mode audit
python -m shadowqueen.cli --db sq.db scan policy_events.json --policy-mode apply
python -m shadowqueen.cli --db sq.db stats
python -m shadowqueen.cli --db sq.db list policy_actions
python -m shadowqueen.cli --db sq.db list denylist
python -m shadowqueen.cli --db sq.db list watchlist
```
