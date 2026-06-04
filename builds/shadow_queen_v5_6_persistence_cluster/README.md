# Shadow Queen v5.6 — Persistence Cluster

## Added
- multi-node persistent state
- peer registry
- change log
- state hash
- snapshots
- snapshot restore
- node sync
- divergence detection
- conflict records
- peer recovery
- evidence export

## Run
```bash
python selftest.py
python -m shadowqueen.cli demo
python -m shadowqueen.cli --db cluster.db --node office:north status
python -m shadowqueen.cli --db cluster.db --node office:north evidence cluster_evidence.zip
```
