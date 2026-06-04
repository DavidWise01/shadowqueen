"""
Terra Prime Kernel v4.6a — Adaptive Clone Fingerprint Memory
"""

class CloneFingerprintMemory:
    def __init__(self):
        self.memory = {}

    def remember(self, fingerprint, decision):
        if decision != "allow":
            self.memory[fingerprint] = decision

    def classify(self, fingerprint, delta, class_hint):
        if fingerprint in self.memory:
            return self.memory[fingerprint]
        if delta == "0.00000000" and class_hint != "clean_clone":
            return "track"
        if class_hint == "clean_clone":
            return "allow"
        if class_hint == "shadow_clone":
            return "quarantine_reflection"
        if class_hint == "phase_clone":
            return "phase_lock"
        return "track"

def v46a_law():
    return "once a fingerprint deviates, later zero-looking states do not erase provenance"
