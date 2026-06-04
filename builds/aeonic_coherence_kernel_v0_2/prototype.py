"""
Aeonic Coherence Kernel v0.2

Compact runnable demo:
- 11+1 core
- truth / bridge / weak shadow
- two observers
- hash ledger
- external validation interface
- retrieval gate
"""

import math, random, statistics, hashlib, json
from dataclasses import dataclass

@dataclass
class EvidencePacket:
    source_id: str
    claim_value: float
    confidence: float
    freshness: float
    relevance: float
    provenance: str

class ExternalValidationInterface:
    def __init__(self, seed=202):
        self.rng = random.Random(seed)

    def retrieve(self, candidate_value, stress=0.0):
        packets = []
        for i in range(5):
            sign = self.rng.choice([-1, 1])
            claim = candidate_value * sign * (0.55 + self.rng.random() * 0.55) + self.rng.gauss(0, 0.10 + 0.08 * stress)
            packets.append(EvidencePacket(
                f"src_{i+1}",
                claim,
                max(0.1, min(1, 0.55 + self.rng.random() * 0.4 - stress * 0.05)),
                max(0.1, min(1, 0.70 + self.rng.gauss(0, 0.15))),
                max(0.1, min(1, 0.65 + self.rng.gauss(0, 0.18))),
                "simulated_external_source"
            ))
        return packets

class EvidenceScorer:
    def score(self, candidate_value, packets):
        support = contradiction = weight_total = 0.0
        for p in packets:
            w = p.confidence * p.freshness * p.relevance
            agreement = 1 - min(1, abs(candidate_value - p.claim_value) / 2.5)
            opposition = min(1, abs(candidate_value + p.claim_value) / 2.5)
            if p.claim_value * candidate_value >= 0:
                support += w * agreement
            else:
                contradiction += w * opposition
            weight_total += w
        weight_total = weight_total or 1.0
        support /= weight_total
        contradiction /= weight_total
        uncertainty = max(0, min(1, 1 - abs(support - contradiction)))
        return {"support": support, "contradiction": contradiction, "uncertainty": uncertainty, "packet_count": len(packets)}

class EvidenceObserver:
    def observe(self, score):
        warning = 0.45 * score["contradiction"] + 0.35 * score["uncertainty"] + 0.20 * max(0, 0.45 - score["support"])
        warning = max(0, min(1, warning))
        return {"evidence_warning": warning, "evidence_alert": warning > 0.72}

class RetrievalGate:
    def pass_signal(self, score, obs):
        return {
            "support_signal": 0.06 * score["support"],
            "contradiction_signal": 0.08 * score["contradiction"],
            "uncertainty_signal": 0.05 * score["uncertainty"],
            "warning_signal": 0.07 * obs["evidence_warning"],
        }

class ObserverA:
    def observe(self, row):
        deviation = abs(row["self_state"])
        trust = max(0, min(1, .35*row["stability"] + .25*row["adaptive_score"] + .20*(1-min(1,deviation)) + .20*(1-min(1,row["rigidity"]))))
        return {"trust": trust, "alert": trust < .62 or row["stability"] < .70}

class ObserverB:
    def __init__(self):
        self.prev = None
    def observe(self, row):
        delta = 0 if self.prev is None else abs(row["self_state"] - self.prev["self_state"])
        anomaly = max(0, min(1, .35*delta + .25*abs(row["correction"]) + .20*row["shadow_load"] + .20*row["bridge_load"]))
        self.prev = row
        return {"anomaly": anomaly, "alert": anomaly > .38 or row["stability"] < .70}

class Ledger:
    def __init__(self, window=16):
        self.records = []
        self.prev_hash = "0"*64
        self.warning = 0.0
        self.window = window
    def pre_warning(self):
        return self.warning
    def store(self, row, obs_a, obs_b, evidence, evidence_obs):
        recent = self.records[-self.window:]
        if recent:
            avg_stab = sum(r["stability"] for r in recent)/len(recent)
            avg_trust = sum(r["observer_a_trust"] for r in recent)/len(recent)
            avg_anom = sum(r["observer_b_anomaly"] for r in recent)/len(recent)
            avg_ev = sum(r["evidence_warning"] for r in recent)/len(recent)
            raw = .30*max(0,.86-avg_stab) + .20*max(0,.72-avg_trust) + .20*min(1,avg_anom*3) + .30*avg_ev
        else:
            raw = 0.0
        self.warning = .80*self.warning + .20*max(0,min(1,raw))
        payload = {
            "cycle": row["cycle"],
            "self_state": row["self_state"],
            "stability": row["stability"],
            "observer_a_trust": obs_a["trust"],
            "observer_b_anomaly": obs_b["anomaly"],
            "evidence_support": evidence["support"],
            "evidence_contradiction": evidence["contradiction"],
            "evidence_uncertainty": evidence["uncertainty"],
            "evidence_warning": evidence_obs["evidence_warning"],
            "ledger_warning": self.warning,
            "previous_hash": self.prev_hash,
        }
        h = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        payload["hash"] = h
        self.prev_hash = h
        self.records.append(payload)
        return payload

class KernelV02:
    def __init__(self, seed=1109):
        self.rng = random.Random(seed)
        self.self_state = self.memory = self.prediction = self.correction = 0.0
        self.bridge_state = self.shadow_state = self.truth_state = 0.0
        self.shadow_memory = []
        self.truth_memory = []
        self.phase = 0.0
        self.external = ExternalValidationInterface()
        self.scorer = EvidenceScorer()
        self.evidence_observer = EvidenceObserver()
        self.gate = RetrievalGate()
        self.obs_a = ObserverA()
        self.obs_b = ObserverB()
        self.ledger = Ledger()

    def step(self, cycle, noise=.02, contradiction=0, pressure=1, drift=0, external_stress=0):
        ledger_warning = self.ledger.pre_warning()
        self.phase += math.tau / 11
        candidates = []
        for i in range(11):
            angle = self.phase + i*math.tau/11
            value = (math.sin(angle) + .17*self.memory + .14*self.prediction + .15*self.bridge_state + .10*self.truth_state
                     - .09*self.shadow_state + contradiction*math.sin(angle*2+math.pi) + drift*(i-5)/5 + self.rng.gauss(0,noise))
            coherence = 1-min(1, abs(value-self.self_state)/2.5)
            anchor_fit = 1-min(1, abs(value)/2.5)
            bridge_fit = 1-min(1, abs(value-self.bridge_state)/2.5)
            truth_fit = 1-min(1, abs(value-self.truth_state)/2.5)
            shadow_penalty = min(1, abs(value-self.shadow_state)/3)
            conf = max(0,min(1,.39*coherence+.24*anchor_fit+.15*bridge_fit+.14*truth_fit+.08*shadow_penalty))
            conf = max(0,min(1, conf - .03*ledger_warning*abs(value-self.self_state)))
            candidates.append({"channel":i+1,"value":value,"confidence":conf})
        strongest = max(candidates, key=lambda c:c["confidence"])
        packets = self.external.retrieve(strongest["value"], stress=external_stress)
        evidence = self.scorer.score(strongest["value"], packets)
        evidence_obs = self.evidence_observer.observe(evidence)
        gate = self.gate.pass_signal(evidence, evidence_obs)

        high = sorted(candidates, key=lambda c:c["confidence"], reverse=True)[:3]
        truth_sample = sum(c["value"]*c["confidence"] for c in high)/(sum(c["confidence"] for c in high) or 1)
        truth_sample += gate["support_signal"] - gate["uncertainty_signal"]
        self.truth_memory.append(truth_sample); self.truth_memory = self.truth_memory[-16:]
        self.truth_state = .88*self.truth_state + .12*(sum(self.truth_memory)/len(self.truth_memory))
        truth_load = min(1, abs(self.truth_state)/1.8)

        rejected = [c for c in candidates if c["channel"] != strongest["channel"]]
        low = sorted(rejected, key=lambda c:c["confidence"])[:4]
        shadow_pressure = sum(c["value"]*(1-c["confidence"]) for c in low)/len(low)
        shadow_pressure += gate["contradiction_signal"] + gate["warning_signal"]
        self.shadow_memory.append(shadow_pressure); self.shadow_memory = self.shadow_memory[-24:]
        weights = [.88**i for i in range(len(self.shadow_memory)-1,-1,-1)]
        archive = sum(v*w for v,w in zip(self.shadow_memory,weights))/(sum(weights) or 1)
        self.shadow_state = .82*self.shadow_state + .18*archive
        shadow_load = min(1, abs(self.shadow_state)/1.8)

        total_w = sum(c["confidence"]**2 for c in candidates) or 1
        weighted_center = sum(c["value"]*(c["confidence"]**2) for c in candidates)/total_w
        low_avg = sum(c["value"] for c in low)/len(low)
        bridge_output = .55*weighted_center + .19*strongest["value"] + .09*low_avg + .07*shadow_pressure + .07*truth_sample + .03*(gate["support_signal"]-gate["contradiction_signal"])
        self.bridge_state = .80*self.bridge_state + .20*bridge_output
        bridge_load = min(1, abs(strongest["value"]-low_avg)/2.5)

        prev = self.self_state
        self.memory = .86*self.memory + .14*self.self_state
        self.prediction = self.self_state + (self.self_state-prev)
        self.correction = bridge_output-self.prediction
        total_warning = max(ledger_warning, evidence_obs["evidence_warning"]*.20)
        update_rate = .30*(1-.14*shadow_load+.04*truth_load)
        update_rate *= (1-.20*total_warning)
        update_rate = max(.16, min(.36, update_rate))
        self.self_state = (1-update_rate)*self.self_state + update_rate*(bridge_output-.16*pressure*self.correction)

        continuity = 1-min(1, abs(self.self_state-prev))
        anchor_fit = 1-min(1, abs(self.self_state))
        correction_size = min(1, abs(self.correction))
        spread = statistics.pstdev([c["value"] for c in candidates])
        spread_score = 1-min(1, spread/1.6)
        stability = max(0,min(1,.25*continuity+.20*anchor_fit+.15*(1-correction_size)+.11*spread_score+.08*(1-bridge_load)+.06*(1-shadow_load)+.08*(1-min(1,truth_load*.7))+.07*(1-evidence_obs["evidence_warning"])))
        rigidity = max(0,min(1,strongest["confidence"]-spread_score*.18-bridge_load*.10-shadow_load*.10+truth_load*.04))
        adaptive = max(0,min(1,stability*(1-abs(stability-.83))))

        row = {"cycle":cycle,"self_state":round(self.self_state,6),"stability":round(stability,6),"adaptive_score":round(adaptive,6),
               "rigidity":round(rigidity,6),"truth_load":round(truth_load,6),"bridge_load":round(bridge_load,6),
               "shadow_load":round(shadow_load,6),"correction":round(self.correction,6),
               "evidence_support":round(evidence["support"],6),"evidence_contradiction":round(evidence["contradiction"],6),
               "evidence_uncertainty":round(evidence["uncertainty"],6),"evidence_warning":round(evidence_obs["evidence_warning"],6)}
        oa = self.obs_a.observe(row)
        ob = self.obs_b.observe(row)
        led = self.ledger.store(row, oa, ob, evidence, evidence_obs)
        return row, oa, ob, evidence, evidence_obs, led

def demo():
    k = KernelV02()
    for t in range(1,221):
        row, oa, ob, ev, evo, led = k.step(
            t,
            noise=.04+t*.0025,
            contradiction=min(1.1,t*.006),
            pressure=1+t*.012,
            drift=min(1.0,t*.005),
            external_stress=min(1.0,t*.004)
        )
    print("Final stability:", row["stability"])
    print("Evidence warning:", row["evidence_warning"])
    print("Ledger warning:", round(led["ledger_warning"], 6))
    print("Observer A alert:", oa["alert"])
    print("Observer B alert:", ob["alert"])
    print("Final hash:", led["hash"])

if __name__ == "__main__":
    demo()
