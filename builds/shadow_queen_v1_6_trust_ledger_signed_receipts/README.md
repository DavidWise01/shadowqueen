# Shadow Queen v1.6 — Trust Ledger + Signed Receipts

## New

- append-only trust ledger
- chained receipt hashes
- ledger verification command
- receipts for identity issue, decisions, conflicts, and audits
- evidence bundle includes ledger

## Run

```bash
python selftest.py
python -m shadowqueen.cli --db dmv.db --office north process office_events.json
python -m shadowqueen.cli --db dmv.db --office north federate remote_registry_conflict.json --remote-office south
python -m shadowqueen.cli --db dmv.db --office north audit --auditor auditor-1
python -m shadowqueen.cli --db dmv.db --office north verify-ledger
python -m shadowqueen.cli --db dmv.db --office north evidence trust_evidence.zip
```
