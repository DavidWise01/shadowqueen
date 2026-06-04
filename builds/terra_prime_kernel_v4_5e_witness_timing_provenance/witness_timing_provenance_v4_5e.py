"""
v4.5e Witness / Timing Provenance Layer
"""

def pulse_timing_proof(payload):
    return (
        payload.get("carrier") == "3-2-1-0"
        and payload.get("silence_depth") is not None
        and payload.get("rest_taken", False)
    )

def exterior_witness_check(payload):
    return (
        payload.get("register_size") == 256
        and payload.get("witness_index") == 257
        and payload.get("witness_internal", True) is False
    )

def timing_provenance_gate(payload):
    return (
        pulse_timing_proof(payload)
        and exterior_witness_check(payload)
        and payload.get("phase_attribution_lock", False)
        and payload.get("triple_contradiction_pass", False)
    )

def v45e_law():
    return "external witness must prove rest, not just emit signal"
