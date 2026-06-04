# Shadow Queen v2.6 — Federated Credential Replication

v2.5 moved events. v2.6 applies those events into mirrored credential state.

## New

- replicated credential table
- credential mirror table
- event application
- stale event detection
- missing transition conflict
- proof conflict detection
- credential convergence audit
- replication evidence bundle

## Run

```bash
python selftest.py
python -m shadowqueen.cli --db north.db --office north issue C-1 carbon:root --type license --proof-hash proof-1 --targets south,east
python -m shadowqueen.cli --db north.db --office north transition credential_suspended C-1 --targets south,east --version 2
python -m shadowqueen.cli --db north.db --office north credentials
python -m shadowqueen.cli --db north.db --office north verify-ledger
python -m shadowqueen.cli --db north.db --office north evidence credential_replication_evidence.zip
```
