# Shadow Queen v1.5 — Federation + External Audit

## New

- office IDs
- federated registry comparison
- cross-office conflict detection
- external auditor review
- evidence bundle export

## Run

```bash
python selftest.py
python -m shadowqueen.cli --db dmv.db --office north process office_events.json
python -m shadowqueen.cli --db dmv.db --office north registry
python -m shadowqueen.cli --db dmv.db --office north federate remote_registry_conflict.json --remote-office south
python -m shadowqueen.cli --db dmv.db --office north audit --auditor auditor-1
python -m shadowqueen.cli --db dmv.db --office north evidence federation_evidence.zip
```
