# Shadow Queen v5.2 — Real Crypto Upgrade

## Added
- Ed25519 key generation
- PEM key files
- public/private key separation
- public key export/import
- trust store
- signed envelope v2
- real signature verification
- credential signatures
- presentation signatures
- authority signatures
- rotation history
- revocation list
- crypto self-test suite

## Run
```bash
python selftest.py
python -m shadowqueen.cli demo
python -m shadowqueen.cli --db real_crypto.db --node office:north status
python -m shadowqueen.cli --db real_crypto.db --node office:north evidence real_crypto_evidence.zip
```
