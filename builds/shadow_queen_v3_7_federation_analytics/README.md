# Shadow Queen v3.7 — Federation Analytics

## New
- federation metric events
- office risk scoring
- trust/risk analytics
- dashboard generation
- recommendation generation
- analytics evidence export

## Run
```bash
python selftest.py
python -m shadowqueen.cli --db analytics.db demo
python -m shadowqueen.cli --db analytics.db dashboard
python -m shadowqueen.cli --db analytics.db verify-ledger
python -m shadowqueen.cli --db analytics.db evidence analytics_evidence.zip
```
