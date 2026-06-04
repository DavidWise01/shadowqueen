# Shadow Queen v2.5 — Federated Event Bus

## New

- event_id
- event_hash
- origin_office
- causal_chain
- federation receipts
- delivery status
- replay-safe inbox/outbox
- duplicate event detection
- convergence audit
- evidence bundle export

## Run

```bash
python selftest.py
python -m shadowqueen.cli --db north.db --office north publish credential_issued C-1 '{"subject":"carbon:root"}' --targets south,east
python -m shadowqueen.cli --db north.db --office north events
python -m shadowqueen.cli --db north.db --office north verify-ledger
python -m shadowqueen.cli --db north.db --office north evidence event_bus_evidence.zip
```
