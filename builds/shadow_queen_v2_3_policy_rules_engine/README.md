# Shadow Queen v2.3 — Policy Rules Engine

## New

- role-based policy rules
- eligibility checks
- renewal window enforcement
- suspension/revocation rules
- auditor finding requirement
- policy denial reasons
- policy audit table
- ledger-backed policy decisions

## Run

```bash
python selftest.py
python -m shadowqueen.cli --db policy.db --actor reg1 --role registrar --trust 0.9 issue C-1 carbon:root --type license --ttl 30 --proof-hash proof
python -m shadowqueen.cli --db policy.db --actor clerk1 --role clerk --trust 0.8 suspend C-1 --reason review
python -m shadowqueen.cli --db policy.db --actor aud1 --role auditor --trust 0.9 revoke C-1 --finding --reason fraud
python -m shadowqueen.cli --db policy.db policy-audit
python -m shadowqueen.cli --db policy.db verify-ledger
```
