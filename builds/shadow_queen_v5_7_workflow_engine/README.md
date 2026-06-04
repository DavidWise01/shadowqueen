# Shadow Queen v5.7 — Workflow Engine

## Added
- workflow definitions
- state machines
- credential renewal
- credential transfer
- suspension
- appeal
- case review
- operator decisions
- task queue
- citizen status tracking
- audit log
- invalid transition rejection
- evidence export

## Run
```bash
python selftest.py
python -m shadowqueen.cli demo
python -m shadowqueen.cli --db workflow.db --office office:north status
python -m shadowqueen.cli --db workflow.db --office office:north queue
python -m shadowqueen.cli --db workflow.db --office office:north evidence workflow_evidence.zip
```
