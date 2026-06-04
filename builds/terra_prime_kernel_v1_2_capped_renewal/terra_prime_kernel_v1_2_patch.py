
"""
Terra Prime Kernel v1.2 — Capped Renewal Patch

This patch fixes v1.1 runaway renewal.

Real improvement criteria:
- Fewer runaway variants
- More honest recursion
- Lower field charge peaks
- Lower observer alerts
- No fake viability inflation from body spam
"""

MAX_VARIANTS = 12
RENEWAL_COOLDOWN = 21
MIN_LATTICE_FOR_BIRTH = 0.78
MAX_FIELD_CHARGE_FOR_BIRTH = 0.82

def can_renew(field, event, elder_feedback):
    if field.new_variants >= MAX_VARIANTS:
        return False
    if field.cycle - getattr(field, "last_renewal_cycle", -999) < RENEWAL_COOLDOWN:
        return False
    if field.lattice < MIN_LATTICE_FOR_BIRTH:
        return False
    if field.field_charge > MAX_FIELD_CHARGE_FOR_BIRTH:
        return False

    pressure = event.novelty + elder_feedback + max(0.0, 0.78 - field.lattice)
    return pressure > 0.92

def renewal(field, event, elder_feedback):
    if not can_renew(field, event, elder_feedback):
        return None

    field.renewal_cycles += 1
    field.new_variants += 1
    field.last_renewal_cycle = field.cycle

    # Spawn one bounded variant.
    # It starts weak, must earn trust, and cannot multiply immediately.
    variant = {
        "name": choose_variant_type(event),
        "trust": 0.52,
        "fatigue": 0.12,
        "charge": 0.08,
        "probation": 55,
        "authority": 0.0
    }
    return variant

def choose_variant_type(event):
    if event.kind == "extreme":
        return "Storm Sentinel"
    if event.kind == "contradiction":
        return "Bridge Builder"
    if event.kind == "drift":
        return "Dream Cartographer"
    return "Adaptive Healer"
