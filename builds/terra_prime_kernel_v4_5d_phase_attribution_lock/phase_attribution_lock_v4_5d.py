"""
Terra Prime Kernel v4.5d — Phase-Attribution Lock
"""

def phase_attribution_lock(payload):
    emission_hash = payload.get("emission_hash")
    reflection_hash = payload.get("reflection_hash")
    direction_marker = payload.get("direction_marker")
    return (
        emission_hash is not None
        and reflection_hash is not None
        and emission_hash != reflection_hash
        and direction_marker in ("+1", "-1", "0")
    )

def neutral_countersign(payload):
    return (
        payload.get("neutral_signature", False)
        and payload.get("light_countersign", False)
        and payload.get("shadow_countersign", False)
        and not payload.get("neutral_self_certified", True)
    )

def triple_contradiction_pass(payload):
    return (
        payload.get("contradiction_pass_a", False)
        and payload.get("contradiction_pass_b", False)
        and payload.get("contradiction_pass_c", False)
        and payload.get("evaluator_a") != payload.get("evaluator_b")
        and payload.get("evaluator_b") != payload.get("evaluator_c")
        and payload.get("evaluator_a") != payload.get("evaluator_c")
    )

def v45d_law():
    return "phase identity cannot flip without a new provenance chain"
