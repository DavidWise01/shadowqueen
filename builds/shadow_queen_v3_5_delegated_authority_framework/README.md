# Shadow Queen v3.5 — Delegated Authority Framework

## New
- authority principals
- scoped authority grants
- permission checks
- expiration windows
- delegation parent records
- grant revocation
- child-delegation revocation
- authority proofs
- authority decision audit
- evidence export

## Run
```bash
python selftest.py
python -m shadowqueen.cli --db authority.db demo
python -m shadowqueen.cli --db authority.db grants
python -m shadowqueen.cli --db authority.db decisions
python -m shadowqueen.cli --db authority.db verify-ledger
python -m shadowqueen.cli --db authority.db evidence authority_evidence.zip
```
