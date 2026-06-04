# Shadow Queen v2.2 — Credential Lifecycle Engine

## New

- credential issuance
- renewal
- suspension
- revocation
- expiration processing
- replacement
- credential history
- chain-of-custody table
- invalid transition detection
- evidence bundle with lifecycle records + ledger

## Run

```bash
python selftest.py
python -m shadowqueen.cli --db cred.db issue C-1 carbon:root --type driver_license --ttl 365 --proof-hash proof-abc
python -m shadowqueen.cli --db cred.db suspend C-1 --reason "review"
python -m shadowqueen.cli --db cred.db renew C-1 C-2
python -m shadowqueen.cli --db cred.db revoke C-2 --reason "fraud"
python -m shadowqueen.cli --db cred.db history
python -m shadowqueen.cli --db cred.db verify-ledger
python -m shadowqueen.cli --db cred.db evidence credential_evidence.zip
```
