# Terra Prime Kernel v4.6a — Adaptive Clone Fingerprint Memory

## Purpose

v4.6 failed because some clone jitter collapsed back to:

```text
0.00000000
```

That made anomalies look clean for one instant.

v4.6a fixes that with persistent adaptive fingerprint memory.

## Core Rule

```text
once a fingerprint deviates
later zero-looking states do not erase provenance
```

## Result

```text
previous missed anomalies: 2666
new missed anomalies: 0
false positives: 0
```
