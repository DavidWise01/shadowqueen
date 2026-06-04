# Shadow Queen v3.9 — Operator Interface

## New
- operator dashboard
- dashboard cards
- work queues
- review queue
- review decisions
- release checks
- operator action log
- release-readiness dashboard
- evidence export

## Run
```bash
python selftest.py
python -m shadowqueen.cli --db operator.db demo
python -m shadowqueen.cli --db operator.db dashboard
python -m shadowqueen.cli --db operator.db verify-ledger
python -m shadowqueen.cli --db operator.db evidence operator_interface_evidence.zip
```
