# Shadow Queen v2.9 — Trust / Reputation Engine

v2.8 detects fraud. v2.9 converts identity, credential, office, graph, and fraud signals into trust scores.

## New

- subject registry
- trust signals
- reputation edges
- computed trust scores
- severity bands: trusted / watch / review / quarantine
- fraud finding ingestion hook
- trust audit
- evidence bundle export

## Run

```bash
python selftest.py
python -m shadowqueen.cli --db trust.db --office north demo
python -m shadowqueen.cli --db trust.db --office north scores
python -m shadowqueen.cli --db trust.db --office north audit --auditor auditor-1
python -m shadowqueen.cli --db trust.db --office north verify-ledger
python -m shadowqueen.cli --db trust.db --office north evidence trust_evidence.zip
```
