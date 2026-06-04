# Shadow Queen v1.8 — Trust Graph

Identity proof becomes relationship graph.

## Identity domains

```text
carbon  = external user
silicon = internal user
```

The engine only uses the distinction as a compute domain boundary.

## New

- Carbon/Silicon identity nodes
- trust edges
- parent / child / issuer / validator / witness / auditor / clone / shadow_clone relationships
- lineage path lookup
- clone and shadow-clone findings
- carbon/silicon boundary validation
- trust ledger retained

## Run

```bash
python selftest.py
python -m shadowqueen.cli --db trust.db ingest sample_graph.json
python -m shadowqueen.cli --db trust.db nodes
python -m shadowqueen.cli --db trust.db edges
python -m shadowqueen.cli --db trust.db findings
python -m shadowqueen.cli --db trust.db lineage silicon:shadow-clone
python -m shadowqueen.cli --db trust.db verify-ledger
python -m shadowqueen.cli --db trust.db evidence trust_graph_evidence.zip
```
