"""
Terra Prime Kernel v4.5j — Silicon-Live Soak
"""

def governor_decay(debt, quarantine):
    if quarantine > 0:
        quarantine -= 1
        debt = min(0, debt + 4)
    return debt, quarantine

def reentry_allowed(source_state):
    return (
        source_state.get("quarantine", 1) == 0
        and source_state.get("debt", -999) > -422
        and source_state.get("witness_timing_pass", False)
        and source_state.get("wiggle_valid", False)
    )

def v45j_law():
    return "quarantine decays, but re-entry still requires witness timing and wiggle proof"
