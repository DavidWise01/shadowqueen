# Shadow Queen v0.5

5-body contained-chaos topology integration.

Integrated source: `five-body-system.html`  
SHA256: `2a49cfc8362f44cd40f8595e847e470c976e0055965d7fb34d62588f1ead35c5`

## Rule

```text
inner 3 = SELF / RING / EXT
outer 2 = +8 CARRIER / -8 SHADOW
inner chaos may vary
outer observers must remain separated
gap must not be crossed
payload must not be read
```

## Run

```bash
python selftest.py
python -m shadowqueen.cli --db sq.db scan five_body_events.json
python -m shadowqueen.cli --db sq.db stats --recent 10
```
