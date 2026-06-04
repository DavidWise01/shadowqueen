# Shadow Queen v5.0 — Distributed Runtime

## Added
- node runtime
- peer registry
- node discovery
- signed message envelopes
- inbox / outbox transport
- heartbeat protocol
- replication protocol
- mesh status
- runtime evidence export

## Run
```bash
python selftest.py
python -m shadowqueen.cli demo
python -m shadowqueen.cli --db runtime.db --node office:north status
python -m shadowqueen.cli --db runtime.db --node office:north evidence runtime_evidence.zip
```
