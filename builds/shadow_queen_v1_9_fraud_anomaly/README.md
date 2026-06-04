# Shadow Queen v1.9 — Fraud + Anomaly Detection

## New

- fraud/anomaly scoring
- shared proof hash detection
- low trust score detection
- clone / shadow-clone risk scoring
- unvalidated Carbon/Silicon boundary detection
- multiple issuer detection
- evidence bundle with findings + ledger

## Run

```bash
python selftest.py
python -m shadowqueen.cli --db fraud.db ingest fraud_graph.json
python -m shadowqueen.cli --db fraud.db findings
python -m shadowqueen.cli --db fraud.db stats
python -m shadowqueen.cli --db fraud.db verify-ledger
python -m shadowqueen.cli --db fraud.db evidence fraud_evidence.zip
```
