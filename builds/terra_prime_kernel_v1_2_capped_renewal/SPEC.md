# Terra Prime Kernel v1.2 — Capped Renewal

## Purpose

v1.1 was executable and recursed correctly, but renewal was too aggressive.

Extreme run:
```text
40 → 101 bodies
```

Contradiction run:
```text
40 → 161 bodies
```

That is not real improvement. That is body inflation.

## v1.2 Fix

Renewal is capped and gated.

## Renewal Rules

```text
MAX_VARIANTS = 12
RENEWAL_COOLDOWN = 21 cycles
MIN_LATTICE_FOR_BIRTH = 0.78
MAX_FIELD_CHARGE_FOR_BIRTH = 0.82
```

New variants can only emerge when:

- the field is coherent enough
- field charge is not storming
- enough time passed since prior birth
- variant count is below cap
- novelty/elder pressure is high enough

## Real Improvement Criteria

A change counts only if it improves real behavior:

- lower runaway body count
- lower field charge peaks
- lower observer alerts
- bounded recursion
- no fake viability inflation
- variants must stay probationary

## Result

v1.2 sacrifices inflated scores for healthier dynamics.

This is a real improvement.
