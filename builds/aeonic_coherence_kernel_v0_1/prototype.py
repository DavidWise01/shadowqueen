"""
Aeonic Coherence Kernel v0.1

A minimal runnable prototype of the current kernel:

- 11 dynamic channels
- 1 resolver anchor
- truth validator
- weak shadow
- bridge mediator
- observer A trust audit
- observer B anomaly history
- hash-chain report ledger
- warning feedback

Run:
    python prototype.py
"""

import math
import random
import statistics
import hashlib
import json


class ObserverA:
    def observe(self, row):
        deviation = abs(row["self_state"])
        trust = max(0, min(1,
            0.35 * row["stability"] +
            0.25 * row["adaptive_score"] +
            0.20 * (1 - min(1, deviation)) +
            0.20 * (1 - min(1, row["rigidity"]))
        ))
        return {
            "cycle": row["cycle"],
            "trust": round(trust, 6),
            "deviation": round(deviation, 6),
            "alert": trust < 0.62 or row["stability"] < 0.70,
        }


class ObserverB:
    def __init__(self):
        self.prev = None

    def observe(self, row):
        delta = 0 if self.prev is None else abs(row["self_state"] - self.prev["self_state"])
        anomaly = max(0, min(1,
            0.35 * delta +
            0.25 * abs(row["correction"]) +
            0.20 * row["shadow_load"] +
            0.20 * row["bridge_load"]
        ))
        self.prev = row
        return {
            "cycle": row["cycle"],
            "delta": round(delta, 6),
            "anomaly": round(anomaly, 6),
            "alert": anomaly > 0.38 or row["stability"] < 0.70,
        }


class ReportLedger:
    def __init__(self, window=16):
        self.records = []
        self.previous_hash = "0" * 64
        self.window = window
        self.warning = 0.0

    def pre_warning(self):
        return self.warning

    def store(self, row, obs_a, obs_b):
        recent = self.records[-self.window:]
        if recent:
            avg_stability = sum(r["stability"] for r in recent) / len(recent)
            avg_trust = sum(r["observer_a_trust"] for r in recent) / len(recent)
            avg_anomaly = sum(r["observer_b_anomaly"] for r in recent) / len(recent)
            raw_warning = (
                0.40 * max(0, 0.86 - avg_stability) +
                0.30 * max(0, 0.72 - avg_trust) +
                0.30 * min(1, avg_anomaly * 3.0)
            )
        else:
            raw_warning = 0.0

        self.warning = 0.80 * self.warning + 0.20 * max(0, min(1, raw_warning))

        payload = {
            "cycle": row["cycle"],
            "self_state": row["self_state"],
            "stability": row["stability"],
            "rigidity": row["rigidity"],
            "adaptive_score": row["adaptive_score"],
            "observer_a_trust": obs_a["trust"],
            "observer_a_alert": obs_a["alert"],
            "observer_b_anomaly": obs_b["anomaly"],
            "observer_b_alert": obs_b["alert"],
            "ledger_warning": round(self.warning, 6),
            "previous_hash": self.previous_hash,
        }

        digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
        payload["hash"] = digest
        self.previous_hash = digest
        self.records.append(payload)
        return payload


class AeonicCoherenceKernel:
    def __init__(self, seed=1108):
        self.rng = random.Random(seed)
        self.self_state = 0.0
        self.memory = 0.0
        self.prediction = 0.0
        self.correction = 0.0
        self.bridge_state = 0.0
        self.shadow_state = 0.0
        self.truth_state = 0.0
        self.shadow_memory = []
        self.truth_memory = []
        self.phase = 0.0

        self.observer_a = ObserverA()
        self.observer_b = ObserverB()
        self.ledger = ReportLedger()

    def step(self, cycle, noise=0.02, contradiction=0.0, pressure=1.0, drift=0.0):
        warning = self.ledger.pre_warning()
        self.phase += math.tau / 11

        candidates = []
        for i in range(11):
            angle = self.phase + i * math.tau / 11
            value = (
                math.sin(angle)
                + 0.17 * self.memory
                + 0.14 * self.prediction
                + 0.15 * self.bridge_state
                + 0.10 * self.truth_state
                - 0.09 * self.shadow_state
                + contradiction * math.sin(angle * 2 + math.pi)
                + drift * (i - 5) / 5
                + self.rng.gauss(0, noise)
            )

            coherence = 1 - min(1, abs(value - self.self_state) / 2.5)
            anchor_fit = 1 - min(1, abs(value) / 2.5)
            bridge_fit = 1 - min(1, abs(value - self.bridge_state) / 2.5)
            truth_fit = 1 - min(1, abs(value - self.truth_state) / 2.5)
            shadow_penalty = min(1, abs(value - self.shadow_state) / 3)

            confidence = max(0, min(1,
                0.39 * coherence +
                0.24 * anchor_fit +
                0.15 * bridge_fit +
                0.14 * truth_fit +
                0.08 * shadow_penalty
            ))

            confidence = max(0, min(1, confidence - 0.03 * warning * abs(value - self.self_state)))
            candidates.append({"channel": i + 1, "value": value, "confidence": confidence})

        strongest = max(candidates, key=lambda c: c["confidence"])

        high = sorted(candidates, key=lambda c: c["confidence"], reverse=True)[:3]
        truth_sample = sum(c["value"] * c["confidence"] for c in high) / (sum(c["confidence"] for c in high) or 1)
        self.truth_memory.append(truth_sample)
        self.truth_memory = self.truth_memory[-16:]
        self.truth_state = 0.88 * self.truth_state + 0.12 * (sum(self.truth_memory) / len(self.truth_memory))
        truth_load = min(1, abs(self.truth_state) / 1.8)

        rejected = [c for c in candidates if c["channel"] != strongest["channel"]]
        low = sorted(rejected, key=lambda c: c["confidence"])[:4]
        shadow_pressure = sum(c["value"] * (1 - c["confidence"]) for c in low) / len(low)
        self.shadow_memory.append(shadow_pressure)
        self.shadow_memory = self.shadow_memory[-24:]

        weights = [0.88 ** i for i in range(len(self.shadow_memory) - 1, -1, -1)]
        archive = sum(v * w for v, w in zip(self.shadow_memory, weights)) / (sum(weights) or 1)
        self.shadow_state = 0.82 * self.shadow_state + 0.18 * archive
        shadow_load = min(1, abs(self.shadow_state) / 1.8)

        total_weight = sum(c["confidence"] ** 2 for c in candidates) or 1
        weighted_center = sum(c["value"] * (c["confidence"] ** 2) for c in candidates) / total_weight
        low_average = sum(c["value"] for c in low) / len(low)

        bridge_output = (
            0.56 * weighted_center +
            0.20 * strongest["value"] +
            0.09 * low_average +
            0.07 * shadow_pressure +
            0.08 * truth_sample
        )

        self.bridge_state = 0.80 * self.bridge_state + 0.20 * bridge_output
        bridge_load = min(1, abs(strongest["value"] - low_average) / 2.5)

        previous_self = self.self_state
        self.memory = 0.86 * self.memory + 0.14 * self.self_state
        self.prediction = self.self_state + (self.self_state - previous_self)
        self.correction = bridge_output - self.prediction

        update_rate = 0.30 * (1 - 0.14 * shadow_load + 0.04 * truth_load)
        update_rate *= (1 - 0.20 * warning)
        update_rate = max(0.16, min(0.36, update_rate))

        self.self_state = (
            (1 - update_rate) * self.self_state +
            update_rate * (bridge_output - 0.16 * pressure * self.correction)
        )

        continuity = 1 - min(1, abs(self.self_state - previous_self))
        anchor_fit = 1 - min(1, abs(self.self_state))
        correction_size = min(1, abs(self.correction))
        spread = statistics.pstdev([c["value"] for c in candidates])
        spread_score = 1 - min(1, spread / 1.6)

        stability = max(0, min(1,
            0.26 * continuity +
            0.21 * anchor_fit +
            0.16 * (1 - correction_size) +
            0.12 * spread_score +
            0.09 * (1 - bridge_load) +
            0.07 * (1 - shadow_load) +
            0.09 * (1 - min(1, truth_load * 0.7))
        ))

        rigidity = max(0, min(1,
            strongest["confidence"] -
            spread_score * 0.19 -
            bridge_load * 0.11 -
            shadow_load * 0.10 +
            truth_load * 0.05
        ))

        adaptive_score = max(0, min(1, stability * (1 - abs(stability - 0.83))))

        row = {
            "cycle": cycle,
            "self_state": round(self.self_state, 6),
            "stability": round(stability, 6),
            "adaptive_score": round(adaptive_score, 6),
            "rigidity": round(rigidity, 6),
            "truth_load": round(truth_load, 6),
            "bridge_load": round(bridge_load, 6),
            "shadow_load": round(shadow_load, 6),
            "correction": round(self.correction, 6),
            "ledger_warning_input": round(warning, 6),
        }

        obs_a = self.observer_a.observe(row)
        obs_b = self.observer_b.observe(row)
        ledger_record = self.ledger.store(row, obs_a, obs_b)

        return row, obs_a, obs_b, ledger_record


def demo():
    kernel = AeonicCoherenceKernel()

    for t in range(1, 221):
        noise = 0.04 + t * 0.0025
        contradiction = min(1.1, t * 0.006)
        pressure = 1 + t * 0.012
        drift = min(1.0, t * 0.005)

        row, obs_a, obs_b, ledger = kernel.step(t, noise, contradiction, pressure, drift)

    print("Final stability:", row["stability"])
    print("Final warning:", ledger["ledger_warning"])
    print("Observer A alert:", obs_a["alert"])
    print("Observer B alert:", obs_b["alert"])
    print("Final hash:", ledger["hash"])


if __name__ == "__main__":
    demo()
