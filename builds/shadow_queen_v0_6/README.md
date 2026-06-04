# Shadow Queen v0.6

Nested closure integration.

Integrated source: `nested-closure.html`  
SHA256: `3d37d2ed26e8214b3e8e71dba68827bafffccc3d514231d2bd15be4971bfc1c0`

## Rule

```text
((12) 0 0 (34))
nesting, not stacking
```

Meaning:

```text
paired units close as one object
two nulls create an airgap region, not a point
outer wrap makes the whole opaque to parent level
internals must not be exposed upward
ack must not cross the airgap
```

## Run

```bash
python selftest.py
python -m shadowqueen.cli --db sq.db scan nested_closure_events.json
python -m shadowqueen.cli --db sq.db stats --recent 10
```
