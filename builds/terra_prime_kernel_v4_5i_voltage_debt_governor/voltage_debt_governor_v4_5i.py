"""
Terra Prime Kernel v4.5i — Voltage Debt Governor
"""

WIGGLE_PATTERN = ["-", "+", "+", "-"]
SOFT_REJECT_MV = -211
QUARANTINE_MV = -422
PANIC_MV = -844

def wiggle_valid(sequence):
    return list(sequence) == WIGGLE_PATTERN

def debt_class(voltage_debt):
    if voltage_debt <= PANIC_MV:
        return "intercept_before_panic"
    if voltage_debt <= QUARANTINE_MV:
        return "quarantine"
    if voltage_debt <= SOFT_REJECT_MV:
        return "soft_reject"
    return "ok"

def v45i_law():
    return "debt is isolated before it becomes kernel panic"
