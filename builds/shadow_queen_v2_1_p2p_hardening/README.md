# Shadow Queen v2.1 — P2P Hardening

## Added

- nonce replay protection
- message TTL expiration
- rate-limit tracking
- peer trust penalties
- peer quarantine threshold
- rejection reasons
- conflict escalation

## Run

```bash
python selftest.py
python -m shadowqueen.cli --db queen.db --node queen register north --type office --trust 0.9
python -m shadowqueen.cli --db queen.db --node queen send north identity_update '{"person_id":"P-1","fingerprint":"abc"}'
python -m shadowqueen.cli --db queen.db --node queen verify-ledger
```
