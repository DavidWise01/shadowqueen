"""
v4.5b Provenance Hardening + Contradiction Double-Check
"""

def dual_provenance(payload):
    return (
        payload.get("source_chain_valid", False)
        and payload.get("observer_chain_valid", False)
        and payload.get("quarantine_checksum_valid", False)
    )

def contradiction_double_check(payload):
    return (
        payload.get("contradiction_pass_a", False)
        and payload.get("contradiction_pass_b", False)
        and not payload.get("contradiction_risk", True)
    )

def v45b_law():
    return "one check is not enough for external IO"
