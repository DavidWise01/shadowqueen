"""
Terra Prime Kernel v4.5h — Silicon Stack Integration
"""

WIGGLE_PATTERN = ["-", "+", "+", "-"]

STACK = {
    1: {"name": "Quantum Dot", "mv": 422},
    0: {"name": "User Space", "mv": 0},
    -1: {"name": "Kernel", "mv": -211},
    -2: {"name": "Hypervisor", "mv": -422},
    -3: {"name": "SMM/Root", "mv": -633},
    -4: {"name": "PANIC", "mv": -844},
}

def wiggle_valid(sequence):
    return list(sequence) == WIGGLE_PATTERN

def silicon_privilege_gate(payload):
    return (
        payload.get("witness_timing_pass", False)
        and wiggle_valid(payload.get("wiggle_sequence", []))
        and payload.get("voltage_debt_ok", False)
        and payload.get("fail_count", 3) < 3
    )

def fail_closed(fail_count):
    return "PANIC" if fail_count >= 3 else "REJECT"

def v45h_law():
    return "IO must pass witness-timing quarantine and silicon pulse-wiggle privilege proof"
