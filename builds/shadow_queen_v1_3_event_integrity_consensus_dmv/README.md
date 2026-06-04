# Shadow Queen v1.3 — Event Integrity + Consensus DMV

Virtual DMV model:

```text
Shadow Queen = registrar
minions = observer clerks
identity record = name + address + DOB + document id
consensus = quorum over matching record fingerprints
```

## New

- identity records
- minion observer events
- quorum voting
- duplicate event hash table
- dissent detection
- identity registry
- consensus decisions

## Run

```bash
python selftest.py
python -m shadowqueen.cli --db dmv.db process dmv_events.json
python -m shadowqueen.cli --db dmv.db stats
python -m shadowqueen.cli --db dmv.db registry
```
