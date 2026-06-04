"""
Aeonic Coherence Kernel v0.3

Adds active retrieval adapters.

This demo uses simulated adapters:
- trusted adapter
- stale adapter
- noisy adapter
- contradictory adapter

Run:
    python prototype.py
"""

from dataclasses import dataclass, asdict
import random, math, json, hashlib, statistics
from datetime import datetime, timezone


@dataclass
class EvidencePacket:
    source_id: str
    source_type: str
    claim: str
    claim_value: float
    confidence: float
    freshness: float
    relevance: float
    provenance: str
    retrieved_at: str


class SourceAdapter:
    source_type = "base"

    def retrieve(self, candidate_value, cycle):
        raise NotImplementedError


class TrustedAdapter(SourceAdapter):
    source_type = "trusted"

    def __init__(self, seed=1):
        self.rng = random.Random(seed)

    def retrieve(self, candidate_value, cycle):
        return EvidencePacket(
            "trusted_1",
            self.source_type,
            "stable supporting evidence",
            candidate_value * (0.92 + self.rng.gauss(0, 0.04)),
            0.91,
            0.92,
            0.88,
            "high_provenance_simulated",
            datetime.now(timezone.utc).isoformat()
        )


class StaleAdapter(SourceAdapter):
    source_type = "stale"

    def __init__(self, seed=2):
        self.rng = random.Random(seed)

    def retrieve(self, candidate_value, cycle):
        return EvidencePacket(
            "stale_1",
            self.source_type,
            "older supporting evidence",
            candidate_value * (0.75 + self.rng.gauss(0, 0.08)),
            0.74,
            0.28,
            0.72,
            "stale_simulated",
            datetime.now(timezone.utc).isoformat()
        )


class NoisyAdapter(SourceAdapter):
    source_type = "noisy"

    def __init__(self, seed=3):
        self.rng = random.Random(seed)

    def retrieve(self, candidate_value, cycle):
        return EvidencePacket(
            "noisy_1",
            self.source_type,
            "noisy uncertain evidence",
            self.rng.gauss(0, 1.0),
            0.46,
            0.70,
            0.43,
            "low_provenance_simulated",
            datetime.now(timezone.utc).isoformat()
        )


class ContradictoryAdapter(SourceAdapter):
    source_type = "contradictory"

    def __init__(self, seed=4):
        self.rng = random.Random(seed)

    def retrieve(self, candidate_value, cycle):
        return EvidencePacket(
            "contradiction_1",
            self.source_type,
            "contradictory evidence",
            -candidate_value * (0.80 + self.rng.gauss(0, 0.10)),
            0.78,
            0.86,
            0.80,
            "medium_provenance_simulated",
            datetime.now(timezone.utc).isoformat()
        )


class SourceRanker:
    provenance_weights = {
        "high_provenance_simulated": 1.00,
        "medium_provenance_simulated": 0.78,
        "stale_simulated": 0.52,
        "low_provenance_simulated": 0.38,
    }

    def rank(self, packet):
        pw = self.provenance_weights.get(packet.provenance, 0.50)
        return packet.confidence * packet.freshness * packet.relevance * pw


class AdapterObserver:
    def observe(self, packets, ranks):
        if not packets:
            return {"adapter_warning": 1.0, "adapter_alert": True}

        avg_rank = sum(ranks) / len(ranks)
        freshness = sum(p.freshness for p in packets) / len(packets)
        dominance = max(ranks) / (sum(ranks) or 1.0)
        warning = (
            0.35 * max(0, 0.55 - avg_rank) +
            0.25 * max(0, 0.60 - freshness) +
            0.25 * max(0, dominance - 0.72) +
            0.15 * (1 / max(1, len(packets)))
        )
        warning = max(0, min(1, warning))
        return {"adapter_warning": warning, "adapter_alert": warning > 0.65, "avg_rank": avg_rank, "dominance": dominance}


class RetrievalManager:
    def __init__(self):
        self.adapters = [
            TrustedAdapter(),
            StaleAdapter(),
            NoisyAdapter(),
            ContradictoryAdapter(),
        ]
        self.ranker = SourceRanker()
        self.observer = AdapterObserver()

    def retrieve(self, candidate_value, cycle, budget=4):
        packets = [a.retrieve(candidate_value, cycle) for a in self.adapters[:budget]]
        ranks = [self.ranker.rank(p) for p in packets]
        obs = self.observer.observe(packets, ranks)
        return packets, ranks, obs


class EvidenceScorer:
    def score(self, candidate_value, packets, ranks):
        support = contradiction = total = 0.0
        for p, r in zip(packets, ranks):
            agreement = 1 - min(1, abs(candidate_value - p.claim_value) / 2.5)
            opposition = min(1, abs(candidate_value + p.claim_value) / 2.5)
            if p.claim_value * candidate_value >= 0:
                support += r * agreement
            else:
                contradiction += r * opposition
            total += r
        total = total or 1.0
        support /= total
        contradiction /= total
        uncertainty = max(0, min(1, 1 - abs(support - contradiction)))
        return {"support": support, "contradiction": contradiction, "uncertainty": uncertainty}


class KernelV03:
    def __init__(self, seed=303):
        self.rng = random.Random(seed)
        self.phase = 0.0
        self.self_state = 0.0
        self.bridge_state = 0.0
        self.shadow_state = 0.0
        self.truth_state = 0.0
        self.memory = 0.0
        self.prediction = 0.0
        self.correction = 0.0
        self.ledger_hash = "0" * 64
        self.retrieval = RetrievalManager()
        self.scorer = EvidenceScorer()

    def step(self, cycle, stress=0.0):
        self.phase += math.tau / 11
        candidates = []
        for i in range(11):
            angle = self.phase + i * math.tau / 11
            value = math.sin(angle) + 0.15*self.bridge_state + 0.10*self.truth_state - 0.08*self.shadow_state + self.rng.gauss(0, 0.02 + stress*0.08)
            confidence = 1 - min(1, abs(value - self.self_state) / 2.5)
            candidates.append({"channel": i+1, "value": value, "confidence": confidence})

        strongest = max(candidates, key=lambda x: x["confidence"])
        packets, ranks, adapter_obs = self.retrieval.retrieve(strongest["value"], cycle)
        evidence = self.scorer.score(strongest["value"], packets, ranks)

        support_signal = 0.05 * evidence["support"]
        contradiction_signal = 0.07 * evidence["contradiction"]
        uncertainty_signal = 0.05 * evidence["uncertainty"]
        adapter_warning_signal = 0.06 * adapter_obs["adapter_warning"]

        truth_sample = strongest["value"] + support_signal - uncertainty_signal
        shadow_pressure = contradiction_signal + adapter_warning_signal
        self.truth_state = 0.88*self.truth_state + 0.12*truth_sample
        self.shadow_state = 0.86*self.shadow_state + 0.14*shadow_pressure

        center = sum(c["value"] * (c["confidence"]**2) for c in candidates) / (sum(c["confidence"]**2 for c in candidates) or 1)
        bridge_output = 0.62*center + 0.20*strongest["value"] + 0.10*self.truth_state - 0.08*self.shadow_state
        self.bridge_state = 0.80*self.bridge_state + 0.20*bridge_output

        prev = self.self_state
        self.memory = 0.86*self.memory + 0.14*self.self_state
        self.prediction = self.self_state + (self.self_state - prev)
        self.correction = bridge_output - self.prediction
        warning = min(1, evidence["uncertainty"]*0.10 + adapter_obs["adapter_warning"]*0.25)
        update_rate = 0.30 * (1 - 0.20*warning)
        self.self_state = (1-update_rate)*self.self_state + update_rate*(bridge_output - 0.16*self.correction)

        continuity = 1 - min(1, abs(self.self_state - prev))
        correction_score = 1 - min(1, abs(self.correction))
        evidence_score = 1 - min(1, evidence["contradiction"]*0.5 + evidence["uncertainty"]*0.25)
        stability = max(0, min(1, 0.38*continuity + 0.28*correction_score + 0.22*evidence_score + 0.12*(1-adapter_obs["adapter_warning"])))
        adaptive = max(0, min(1, stability * (1 - abs(stability - 0.83))))

        record = {
            "cycle": cycle,
            "self_state": round(self.self_state, 6),
            "stability": round(stability, 6),
            "adaptive_score": round(adaptive, 6),
            "evidence_support": round(evidence["support"], 6),
            "evidence_contradiction": round(evidence["contradiction"], 6),
            "evidence_uncertainty": round(evidence["uncertainty"], 6),
            "adapter_warning": round(adapter_obs["adapter_warning"], 6),
            "adapter_alert": adapter_obs["adapter_alert"],
            "avg_source_rank": round(adapter_obs["avg_rank"], 6),
            "source_dominance": round(adapter_obs["dominance"], 6),
        }

        payload = dict(record)
        payload["previous_hash"] = self.ledger_hash
        self.ledger_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        record["hash"] = self.ledger_hash
        return record


def demo():
    k = KernelV03()
    rows = []
    for t in range(1, 221):
        rows.append(k.step(t, stress=min(1.0, t*0.005)))

    avg_stability = statistics.mean(r["stability"] for r in rows)
    min_stability = min(r["stability"] for r in rows)
    alerts = sum(1 for r in rows if r["adapter_alert"])

    print("Avg stability:", round(avg_stability, 6))
    print("Min stability:", round(min_stability, 6))
    print("Adapter alerts:", alerts)
    print("Final hash:", rows[-1]["hash"])


if __name__ == "__main__":
    demo()
