"""
Aeonic Coherence Kernel v0.4

Multi-agent arbitration.
Tests 1 agent vs 2 agents.

Run:
    python prototype.py
"""

from dataclasses import dataclass
import math, random, statistics, hashlib, json


@dataclass
class AgentProposal:
    agent_id: str
    role: str
    value: float
    confidence: float
    dissent: float
    reputation: float


class Agent:
    def __init__(self, agent_id, role, bias=0.0, skepticism=0.0, seed=1):
        self.agent_id = agent_id
        self.role = role
        self.bias = bias
        self.skepticism = skepticism
        self.reputation = 0.72
        self.rng = random.Random(seed)

    def propose(self, base_value, cycle, stress=0.0):
        phase = math.sin(cycle * 0.11 + self.bias)
        dissent = self.skepticism * math.cos(cycle * 0.07)
        noise = self.rng.gauss(0, 0.035 + stress * 0.05)
        value = base_value + 0.18 * phase - 0.22 * dissent + noise
        confidence = max(0.05, min(1.0, self.reputation - abs(dissent) * 0.10 - stress * 0.04 + self.rng.random() * 0.06))
        return AgentProposal(self.agent_id, self.role, value, confidence, abs(dissent), self.reputation)

    def update_reputation(self, proposal, resolved_value):
        error = abs(proposal.value - resolved_value)
        reward = max(0, 1 - min(1, error))
        self.reputation = 0.94 * self.reputation + 0.06 * reward
        self.reputation = max(0.25, min(0.92, self.reputation))


class AgentArbitrationBridge:
    def arbitrate(self, proposals):
        total = sum((p.confidence * p.reputation) for p in proposals) or 1.0
        consensus = sum(p.value * p.confidence * p.reputation for p in proposals) / total

        if len(proposals) == 1:
            dissent = 0.0
            dominance = 1.0
            contradiction = 0.0
        else:
            values = [p.value for p in proposals]
            dissent = statistics.pstdev(values)
            dominance = max(p.confidence * p.reputation for p in proposals) / total
            contradiction = min(1.0, dissent / 1.5)

        # dissent is allowed, but softened
        arbitration_output = consensus - 0.08 * contradiction
        return {
            "consensus": consensus,
            "dissent": dissent,
            "dominance": dominance,
            "contradiction": contradiction,
            "output": arbitration_output,
        }


class KernelV04:
    def __init__(self, agent_count=2, seed=404):
        self.rng = random.Random(seed)
        self.agent_count = agent_count
        self.phase = 0.0
        self.self_state = 0.0
        self.memory = 0.0
        self.prediction = 0.0
        self.correction = 0.0
        self.bridge_state = 0.0
        self.shadow_state = 0.0
        self.truth_state = 0.0
        self.ledger_hash = "0" * 64
        self.bridge = AgentArbitrationBridge()

        if agent_count == 1:
            self.agents = [Agent("agent_logic", "logic", bias=0.0, skepticism=0.0, seed=1)]
        else:
            self.agents = [
                Agent("agent_logic", "logic", bias=0.0, skepticism=0.0, seed=1),
                Agent("agent_skeptic", "skeptic", bias=1.2, skepticism=0.55, seed=2),
            ]

    def step(self, cycle, stress=0.0, contradiction=0.0):
        self.phase += math.tau / 11

        # 11+1 base field
        candidates = []
        for i in range(11):
            angle = self.phase + i * math.tau / 11
            value = (
                math.sin(angle)
                + 0.16 * self.memory
                + 0.14 * self.prediction
                + 0.14 * self.bridge_state
                + 0.09 * self.truth_state
                - 0.08 * self.shadow_state
                + contradiction * math.sin(angle * 2 + math.pi)
                + self.rng.gauss(0, 0.02 + stress * 0.08)
            )
            confidence = 1 - min(1, abs(value - self.self_state) / 2.5)
            candidates.append({"channel": i + 1, "value": value, "confidence": confidence})

        strongest = max(candidates, key=lambda c: c["confidence"])
        base_value = strongest["value"]

        proposals = [agent.propose(base_value, cycle, stress=stress) for agent in self.agents]
        arb = self.bridge.arbitrate(proposals)

        # truth validates consensus; shadow stores dissent
        self.truth_state = 0.88 * self.truth_state + 0.12 * arb["consensus"]
        self.shadow_state = 0.86 * self.shadow_state + 0.14 * (arb["dissent"] + arb["contradiction"])
        truth_load = min(1, abs(self.truth_state) / 1.8)
        shadow_load = min(1, abs(self.shadow_state) / 1.8)

        center = sum(c["value"] * (c["confidence"] ** 2) for c in candidates) / (sum(c["confidence"] ** 2 for c in candidates) or 1)
        bridge_output = (
            0.52 * center +
            0.28 * arb["output"] +
            0.11 * self.truth_state -
            0.09 * self.shadow_state
        )
        self.bridge_state = 0.80 * self.bridge_state + 0.20 * bridge_output

        prev = self.self_state
        self.memory = 0.86 * self.memory + 0.14 * self.self_state
        self.prediction = self.self_state + (self.self_state - prev)
        self.correction = bridge_output - self.prediction

        warning = min(1, arb["contradiction"] * 0.18 + arb["dominance"] * 0.06)
        update_rate = 0.30 * (1 - 0.18 * warning)
        self.self_state = (1 - update_rate) * self.self_state + update_rate * (bridge_output - 0.16 * self.correction)

        for agent, proposal in zip(self.agents, proposals):
            agent.update_reputation(proposal, self.self_state)

        continuity = 1 - min(1, abs(self.self_state - prev))
        correction_score = 1 - min(1, abs(self.correction))
        dissent_score = 1 - min(1, arb["dissent"])
        dominance_score = 1 - min(1, max(0, arb["dominance"] - 0.72) * 2)
        stability = max(0, min(1,
            0.34 * continuity +
            0.26 * correction_score +
            0.18 * dissent_score +
            0.12 * dominance_score +
            0.10 * (1 - shadow_load)
        ))

        rigidity = max(0, min(1, 0.55 * arb["dominance"] + 0.25 * truth_load + 0.20 * (1 - arb["dissent"])))
        adaptive = max(0, min(1, stability * (1 - abs(stability - 0.83))))

        payload = {
            "cycle": cycle,
            "agent_count": self.agent_count,
            "self_state": round(self.self_state, 6),
            "stability": round(stability, 6),
            "adaptive_score": round(adaptive, 6),
            "rigidity": round(rigidity, 6),
            "agent_consensus": round(arb["consensus"], 6),
            "agent_dissent": round(arb["dissent"], 6),
            "agent_dominance": round(arb["dominance"], 6),
            "agent_contradiction": round(arb["contradiction"], 6),
            "truth_load": round(truth_load, 6),
            "shadow_load": round(shadow_load, 6),
            "correction": round(self.correction, 6),
            "reputations": {a.agent_id: round(a.reputation, 6) for a in self.agents},
        }

        hash_payload = dict(payload)
        hash_payload["previous_hash"] = self.ledger_hash
        self.ledger_hash = hashlib.sha256(json.dumps(hash_payload, sort_keys=True).encode()).hexdigest()
        payload["hash"] = self.ledger_hash
        return payload


def run(agent_count, label, cycles=220, stress_fn=lambda t: 0.0, contradiction_fn=lambda t: 0.0):
    kernel = KernelV04(agent_count=agent_count)
    rows = []
    for t in range(1, cycles + 1):
        rows.append(kernel.step(t, stress=stress_fn(t), contradiction=contradiction_fn(t)))
    return label, rows


def summarize(label, rows):
    return {
        "run": label,
        "agent_count": rows[-1]["agent_count"],
        "cycles": len(rows),
        "avg_stability": round(statistics.mean(r["stability"] for r in rows), 6),
        "min_stability": round(min(r["stability"] for r in rows), 6),
        "final_stability": rows[-1]["stability"],
        "avg_adaptive_score": round(statistics.mean(r["adaptive_score"] for r in rows), 6),
        "avg_rigidity": round(statistics.mean(r["rigidity"] for r in rows), 6),
        "avg_dissent": round(statistics.mean(r["agent_dissent"] for r in rows), 6),
        "avg_dominance": round(statistics.mean(r["agent_dominance"] for r in rows), 6),
        "final_hash": rows[-1]["hash"][:16] + "...",
    }


def demo():
    tests = [
        run(1, "one_agent_normal", stress_fn=lambda t: 0.02, contradiction_fn=lambda t: 0.0),
        run(2, "two_agent_normal", stress_fn=lambda t: 0.02, contradiction_fn=lambda t: 0.0),
        run(1, "one_agent_stress", stress_fn=lambda t: min(1.0, t * 0.005), contradiction_fn=lambda t: min(0.8, t * 0.003)),
        run(2, "two_agent_stress", stress_fn=lambda t: min(1.0, t * 0.005), contradiction_fn=lambda t: min(0.8, t * 0.003)),
    ]
    for label, rows in tests:
        print(json.dumps(summarize(label, rows), indent=2))


if __name__ == "__main__":
    demo()
