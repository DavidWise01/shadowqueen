# Shadow Queen v5.1 — Cryptographic Identity

## Added
- node key registry
- trusted peer keys
- signed messages
- signed credentials
- signed presentations
- signed authority grants
- signature verification
- tamper rejection
- key rotation
- signed ledger receipts
- redacted evidence export

## Run
```bash
python selftest.py
python -m shadowqueen.cli demo
python -m shadowqueen.cli --db crypto.db --node office:north status
python -m shadowqueen.cli --db crypto.db --node office:north evidence crypto_identity_evidence.zip
```

Note: this is a local deterministic proof model using hash-based signatures for simulation. v5.2 should replace this with real Ed25519 keys.
