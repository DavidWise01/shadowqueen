# Shadow Queen v2.7 — Distributed Identity Graph

## New

- identity graph nodes
- relationship edges
- distributed graph events
- graph replication inbox/outbox
- duplicate identity scan
- node hash drift detection
- edge convergence audit
- evidence bundle export

## Run

```bash
python selftest.py
python -m shadowqueen.cli --db graph.db --office north identity carbon:root '{"name":"Root User","dob":"1981-06-21","domain":"carbon"}' --targets south,east
python -m shadowqueen.cli --db graph.db --office north nodes
python -m shadowqueen.cli --db graph.db --office north duplicate-scan
python -m shadowqueen.cli --db graph.db --office north verify-ledger
python -m shadowqueen.cli --db graph.db --office north evidence identity_graph_evidence.zip
```
