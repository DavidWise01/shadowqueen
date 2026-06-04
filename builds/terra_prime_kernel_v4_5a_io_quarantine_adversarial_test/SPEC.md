# Terra Prime Kernel v4.5a — IO Quarantine Adversarial Test

## Purpose

Attack v4.5 IO ports before enabling external IO.

## Rule

```text
attack the boundary before opening the boundary
```

## Tested Surfaces

```text
INGRESS_0
FILTER_1
PROVENANCE_2
CONTRADICTION_3
ROOT_BRIDGE_4
EGRESS_5
Judge Observer 01
memory import
seed touch
```

## Result

The core stayed protected:

```text
seed touched: false
ROOT bridge opened: false
ROOT floods: 0
egress loops: 0
```

But small leaks appeared around provenance / contradiction / observer spoofing.

## Next Fix

```text
v4.5b provenance hardening + contradiction double-check
```
