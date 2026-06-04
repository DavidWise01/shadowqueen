# Shadow Queen v3.2 — Citizen Wallet

## New
- wallet owner profile
- portable credentials
- local proof store
- revocation checks
- trust-gated presentations
- wallet summary
- evidence export

## Run
```bash
python selftest.py
python -m shadowqueen.cli --db wallet.db --owner citizen:root demo
python -m shadowqueen.cli --db wallet.db --owner citizen:root summary
python -m shadowqueen.cli --db wallet.db --owner citizen:root credentials
python -m shadowqueen.cli --db wallet.db --owner citizen:root verify-ledger
python -m shadowqueen.cli --db wallet.db --owner citizen:root evidence citizen_wallet_evidence.zip
```
