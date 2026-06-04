# Shadow Queen v3.6 — Autonomous Investigation Engine

## New
- autonomous case intake
- evidence linking
- rule-based triage
- risk scoring
- recommended actions
- automated action execution
- investigation dashboard
- evidence export

## Run
```bash
python selftest.py
python -m shadowqueen.cli --db investigations.db demo
python -m shadowqueen.cli --db investigations.db dashboard
python -m shadowqueen.cli --db investigations.db cases
python -m shadowqueen.cli --db investigations.db actions
python -m shadowqueen.cli --db investigations.db verify-ledger
python -m shadowqueen.cli --db investigations.db evidence investigation_evidence.zip
```
