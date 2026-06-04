# Shadow Queen v3.1 — Federation Operations Center

## New
- office registry
- office health monitor
- office trust scores
- drift detection
- cross-office credential validation
- federated investigation routing
- office quarantine
- office recovery
- federation dashboard
- evidence export

## Run
```bash
python selftest.py
python -m shadowqueen.cli --db ops.db demo
python -m shadowqueen.cli --db ops.db dashboard
python -m shadowqueen.cli --db ops.db offices
python -m shadowqueen.cli --db ops.db cases
python -m shadowqueen.cli --db ops.db verify-ledger
python -m shadowqueen.cli --db ops.db evidence federation_ops_evidence.zip
```
