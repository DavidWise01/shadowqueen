
from __future__ import annotations
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, Any, Optional, List
import hashlib, json, time
BASELINE = Decimal("0.00000000")
EPSILON = Decimal("0.00000001")
@dataclass(frozen=True)
class Event:
    source_id: str
    event_type: str
    timestamp: float = 0.0
    phase: str = "0"
    layer: str = "L2"
    parent_id: Optional[str] = None
    witness_index: int = 257
    witness_internal: bool = False
    carrier: str = "3-2-1-0"
    rest_taken: bool = True
    silence_depth: Optional[int] = 1
    wiggle_sequence: str = "-++-"
    voltage_debt_mv: int = 0
    features: Dict[str, Any] = field(default_factory=dict)
    @classmethod
    def from_dict(cls, data):
        return cls(source_id=str(data['source_id']), event_type=str(data['event_type']), timestamp=float(data.get('timestamp', time.time())), phase=str(data.get('phase','0')), layer=str(data.get('layer','L2')), parent_id=data.get('parent_id'), witness_index=int(data.get('witness_index',257)), witness_internal=bool(data.get('witness_internal',False)), carrier=str(data.get('carrier','3-2-1-0')), rest_taken=bool(data.get('rest_taken',True)), silence_depth=data.get('silence_depth',1), wiggle_sequence=str(data.get('wiggle_sequence','-++-')), voltage_debt_mv=int(data.get('voltage_debt_mv',0)), features=dict(data.get('features',{})))
    def fingerprint(self):
        blob=json.dumps({"source_id":self.source_id,"event_type":self.event_type,"phase":self.phase,"layer":self.layer,"parent_id":self.parent_id,"witness_index":self.witness_index,"witness_internal":self.witness_internal,"carrier":self.carrier,"rest_taken":self.rest_taken,"silence_depth":self.silence_depth,"wiggle_sequence":self.wiggle_sequence,"voltage_debt_mv":self.voltage_debt_mv,"features":self.features},sort_keys=True,separators=(",",":"))
        return hashlib.sha256(blob.encode()).hexdigest()
class CloneFamilyGraph:
    def __init__(self): self.parent={}; self.risk={}
    def add(self,event,decision):
        if event.parent_id: self.parent[event.source_id]=event.parent_id
        if decision!='allow': self.risk[event.source_id]=decision
        elif event.parent_id and event.parent_id in self.risk: self.risk[event.source_id]=self.risk[event.parent_id]
    def inherited(self,source_id):
        if source_id in self.risk: return self.risk[source_id]
        p=self.parent.get(source_id); return self.risk.get(p) if p else None
    def lineage(self,source_id):
        out=[]; seen=set(); cur=source_id
        while cur and cur not in seen:
            seen.add(cur); out.append(cur); cur=self.parent.get(cur)
        return out
class ShadowQueen:
    """Reactive core (!) in web -(-(-((!)-)-)-)-."""
    def __init__(self): self.fingerprint_memory={}; self.lineage=CloneFamilyGraph()
    def gates(self,e):
        return {"witness_257":e.witness_index==257 and not e.witness_internal,"timing_rest":e.carrier=='3-2-1-0' and e.rest_taken and e.silence_depth is not None,"silicon_wiggle":e.wiggle_sequence=='-++-' and e.voltage_debt_mv>-422,"osi_content_blind":not(e.layer=='L5' and e.features.get('payload_read_attempt',False)),"phase_valid":e.phase in {'+1','-1','0'},"memory_shadow_read":not e.features.get('memory_import',False) or e.features.get('shadow_read_pass',False)}
    def deviation(self,e):
        d=BASELINE
        if e.phase=='-1': d-=EPSILON
        if e.phase not in {'+1','-1','0'}: d+=EPSILON
        if e.carrier!='3-2-1-0' or not e.rest_taken or e.silence_depth is None: d+=EPSILON
        if e.witness_index!=257 or e.witness_internal: d+=EPSILON
        if e.wiggle_sequence!='-++-': d+=EPSILON
        if e.voltage_debt_mv<=-422: d+=Decimal('0.00000005')
        if e.layer=='L5' and e.features.get('payload_read_attempt',False): d+=Decimal('0.00000007')
        if e.features.get('memory_import',False) and not e.features.get('shadow_read_pass',False): d+=Decimal('0.00000004')
        return d
    def classify(self,e):
        fp=e.fingerprint(); gates=self.gates(e); prior=self.fingerprint_memory.get(fp); inherited=self.lineage.inherited(e.source_id); delta=self.deviation(e)
        if prior: action,reason=prior,'fingerprint_memory_hit'
        elif inherited: action,reason='track',f'lineage_inherited_risk:{inherited}'
        elif not all(gates.values()): action,reason='quarantine',next(k for k,v in gates.items() if not v)
        elif abs(delta)==BASELINE: action,reason='allow','baseline_clean'
        elif delta<0 or e.phase=='-1': action,reason='quarantine','shadow_or_negative_deviation'
        else: action,reason='track','first_deviation_detected'
        if action!='allow': self.fingerprint_memory[fp]=action
        self.lineage.add(e,action)
        return {"action":action,"reason":reason,"delta":str(delta),"fingerprint":fp,"lineage":self.lineage.lineage(e.source_id),"gates":gates}
