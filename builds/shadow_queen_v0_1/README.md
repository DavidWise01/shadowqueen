# Shadow Queen v0.1

Reactive AI immune/anomaly prototype.

```text
-(-(-((!)-)-)-)-
```

Run:

```bash
python selftest.py
python -m shadowqueen.cli demo
python -m shadowqueen.cli scan sample_events.json
```

It implements: event normalization, witness/timing gates, silicon wiggle check, OSI content-blind rule, fingerprint memory, clone-family lineage, and allow/track/quarantine decisions.

Not production antivirus yet: no kernel hooks, live packet capture, real malware signatures, model-weight inspection, or OS sandbox enforcement.
