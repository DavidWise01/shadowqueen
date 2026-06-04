# Shadow Queen v2.8 — Fraud Detection Engine

## New

- duplicate identity scoring
- synthetic identity detection
- credential stuffing detection
- suspicious address cluster detection
- relationship anomaly detection
- subject risk scores
- fraud audit
- fraud evidence bundle

## Run

```bash
python selftest.py
python -m shadowqueen.cli --db fraud.db --office north demo
python -m shadowqueen.cli --db fraud.db --office north scores
python -m shadowqueen.cli --db fraud.db --office north findings
python -m shadowqueen.cli --db fraud.db --office north audit --auditor auditor-1
python -m shadowqueen.cli --db fraud.db --office north verify-ledger
python -m shadowqueen.cli --db fraud.db --office north evidence fraud_evidence.zip
```
