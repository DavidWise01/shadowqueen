# Shadow Queen v3.4 — Selective Disclosure Engine

## New
- disclosure policies
- allow-list field release
- required-field proof checks
- redaction map
- trust-gated presentations
- presentation proof hashes
- presentation verification
- evidence export

## Run
```bash
python selftest.py
python -m shadowqueen.cli --db disclosure.db --owner citizen:root demo
python -m shadowqueen.cli --db disclosure.db --owner citizen:root presentations
python -m shadowqueen.cli --db disclosure.db --owner citizen:root verify-ledger
python -m shadowqueen.cli --db disclosure.db --owner citizen:root evidence disclosure_evidence.zip
```
