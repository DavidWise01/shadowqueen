# Shadow Queen v1.4 — DMV Appeals + Revocation

## New

- appeals table
- revocation/status-change table
- active / suspended / revoked states
- second quorum for appeal correction
- evidence log
- evidence bundle export
- manual revoke command

## Run

```bash
python selftest.py
python -m shadowqueen.cli --db dmv.db process issue_events.json
python -m shadowqueen.cli --db dmv.db appeal A-1001 P-1001 "address correction"
python -m shadowqueen.cli --db dmv.db review A-1001 P-1001 appeal_review_events.json
python -m shadowqueen.cli --db dmv.db registry
python -m shadowqueen.cli --db dmv.db evidence evidence.zip
```
