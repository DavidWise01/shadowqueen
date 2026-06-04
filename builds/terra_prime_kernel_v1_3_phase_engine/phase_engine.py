"""
Terra Prime Kernel v1.3 — Phase Engine

LIGHT  (+): 0→9, sentinels guard, closure stabilizes, birth allowed.
DARK   (-): 9→0, sentinels hunt, closure is suspicious, pruning preferred.
SHADOW ( ): 0↔9, overlap, 3 is liminal backdoor, unresolved states preserved.
"""

class PhaseEngine:
    LIGHT = "LIGHT"
    DARK = "DARK"
    SHADOW = "SHADOW"

    def __init__(self):
        self.phase = self.LIGHT
        self.register = 0
        self.phase_switches = 0

    def set_phase(self, phase):
        if phase != self.phase:
            self.phase_switches += 1
        self.phase = phase

    def step_register(self):
        if self.phase == self.LIGHT:
            self.register = (self.register + 1) % 12
        elif self.phase == self.DARK:
            self.register = (self.register - 1) % 12
        else:
            self.register = (self.register + (1 if self.register % 2 == 0 else -1)) % 12
        return self.register

    def direction(self):
        return {"LIGHT":"0→9","DARK":"9→0","SHADOW":"0↔9"}[self.phase]

    def core(self):
        return "[¡]" if self.phase == self.DARK else "[!]"

    def node_role(self, n):
        if n in (4, 8):
            return {"LIGHT":"sentinel_guard","DARK":"hunter","SHADOW":"mirror_sentinel"}[self.phase]
        if n in (5, 7):
            return {"LIGHT":"treasure","DARK":"trap","SHADOW":"liminal"}[self.phase]
        if n == 3:
            return "shadow_backdoor"
        if n == 10:
            return "dark_toggle"
        if n == 11:
            return "shadow_toggle"
        return "path"

    def closure_modifier(self, agreements, spread):
        if self.phase == self.LIGHT:
            return ("close", +0.004, -1) if agreements >= 1 else ("recurse", -0.006, +1)

        if self.phase == self.DARK:
            if agreements >= 1 and spread < 0.055:
                return ("suspicious_close", -0.010, 0)
            if agreements >= 1:
                return ("close_checked", -0.002, -1)
            return ("hunt_recurse", +0.001, +1)

        if agreements == 0:
            return ("shadow_recurse", -0.003, +1)
        if agreements == 3 and spread < 0.040:
            return ("shadow_unresolved", 0.000, 0)
        return ("probabilistic_close", +0.001, -1)

    def renewal_policy(self):
        return {"LIGHT":"birth_allowed","DARK":"prune_preferred","SHADOW":"mutate_preferred"}[self.phase]
