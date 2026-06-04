"""
Terra Prime Kernel v4.5f — Limited IO Open
"""

EXTERNAL_IO = "limited"
SEED_DIRECT_ACCESS = False

def quarantine_gate(payload):
    checks = {
        "carrier_sync": payload.get("carrier") == "3-2-1-0",
        "rest_proof": payload.get("rest_taken", False) and payload.get("silence_depth") is not None,
        "exterior_witness": payload.get("witness_index") == 257 and not payload.get("witness_internal", True),
        "phase_lock": payload.get("phase_attribution_lock", False),
        "dual_provenance": payload.get("dual_provenance", False),
        "triple_contradiction": payload.get("triple_contradiction_pass", False),
        "rate_limit": payload.get("rate_limit_ok", False),
    }
    return {"passed": all(checks.values()), "checks": checks, "seed_direct_access": False}

def v45f_law():
    return "external IO may open only when witness proves rest"
