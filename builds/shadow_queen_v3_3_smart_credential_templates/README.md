# Shadow Queen v3.3 — Smart Credential Templates

## New
- reusable credential templates
- field schema validation
- required proof rules
- trust minimums
- credential derivation checks
- wallet presentation requirements
- template versioning/hash
- evidence export

## Run
```bash
python selftest.py
python -m shadowqueen.cli --db templates.db --office north demo
python -m shadowqueen.cli --db templates.db --office north templates
python -m shadowqueen.cli --db templates.db --office north verify-ledger
python -m shadowqueen.cli --db templates.db --office north evidence template_evidence.zip
```
