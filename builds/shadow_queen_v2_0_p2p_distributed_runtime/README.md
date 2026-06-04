# Shadow Queen v2.0 — Peer-to-Peer Distributed Runtime

## New

- peer node registry
- signed message receipts
- inbox / outbox queues
- offline replay
- conflict queue
- federated trust score
- per-node ledger
- evidence bundle export

## Run

```bash
python selftest.py

python -m shadowqueen.cli --db queen.db --node queen register north --type office --trust 0.9
python -m shadowqueen.cli --db queen.db --node queen send north identity_update '{"person_id":"P-1","fingerprint":"abc"}'
python -m shadowqueen.cli --db queen.db --node queen outbox
python -m shadowqueen.cli --db queen.db --node queen verify-ledger
```

Each peer has its own local DB, ledger, inbox, outbox, and conflict queue.
