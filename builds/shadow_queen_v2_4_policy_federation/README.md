# Shadow Queen v2.4 — Policy Federation + Rule Conflict Resolver

## New

- policy versioning
- policy hash comparison
- cross-office rule import/export
- rule conflict queue
- allow/deny mismatch detection
- rule drift detection
- policy override chain
- federated policy audit
- evidence bundle export

## Run

```bash
python selftest.py
python -m shadowqueen.cli --db fed.db --office north export
python -m shadowqueen.cli --db fed.db --office north import south_policy_bundle.json
python -m shadowqueen.cli --db fed.db --office north conflicts
python -m shadowqueen.cli --db fed.db --office north audit --auditor auditor-1
python -m shadowqueen.cli --db fed.db --office north override renew.registrar south accept_remote --actor queen --reason "accept remote window"
python -m shadowqueen.cli --db fed.db --office north verify-ledger
python -m shadowqueen.cli --db fed.db --office north evidence policy_federation_evidence.zip
```
