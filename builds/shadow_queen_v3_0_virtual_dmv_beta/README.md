# Shadow Queen v3.0 — Virtual DMV Beta

This is the first beta skeleton that ties the Shadow Queen DMV line into usable workflows.

## New

- citizen enrollment
- citizen portal summary
- office queue
- license/credential issuance
- renewal workflow
- revocation workflow
- investigation queue
- trust gate checks
- audit log
- ledger-backed evidence export

## Run

```bash
python selftest.py
python -m shadowqueen.cli --db dmv.db --office north demo
python -m shadowqueen.cli --db dmv.db --office north queue
python -m shadowqueen.cli --db dmv.db --office north stats
python -m shadowqueen.cli --db dmv.db --office north verify-ledger
python -m shadowqueen.cli --db dmv.db --office north evidence dmv_beta_evidence.zip
```

## Beta boundary

v3.0 is still a local prototype. It provides workflow shape and auditability, not a production web service.
