
from dataclasses import dataclass
from pathlib import Path
import random, math, statistics, csv, json

@dataclass
class Body:
    id:int; name:str; cls:str; side:str
    trust:float=.68; fatigue:float=0.; charge:float=0.
    def signal(self,rng,stress,pressure,contradiction):
        base={"light":.58,"shadow":.46,"mercury":.52,"core":.50,"temperament":.51,"meta":.50}.get(self.side,.50)
        push=0
        if self.side=="light": push += contradiction*.055
        if self.side=="shadow": push -= contradiction*.060
        if self.side=="mercury": push += math.sin(contradiction*9)*.04
        return max(0,min(1,base+push+rng.gauss(0,.045+stress*.045)+(self.trust-.5)*.06-self.fatigue*.05-pressure*.025))
    def close(self,decay):
        self.trust=max(.2,min(.94,self.trust+.003-decay*.035)); self.fatigue=min(1,self.fatigue+decay*.35); self.charge*=.88
    def recurse(self,stress):
        self.trust=max(.2,self.trust-.007*stress); self.fatigue=min(1,self.fatigue+.03*stress); self.charge=min(1,self.charge+.035*stress)
    def recover(self,amt):
        self.fatigue=max(0,self.fatigue-amt); self.trust=min(.94,self.trust+amt*.2); self.charge=max(0,self.charge-amt*.2)

@dataclass
class Generation:
    age:int; mode:str="active"; wisdom:float=.2; observation:float=.2
    def step(self):
        self.age += 1
        if self.age>=55 and self.mode=="active":
            self.mode="elder"; self.wisdom=min(1,self.wisdom+.25); self.observation=min(1,self.observation+.35)
    def feedback(self):
        return 0 if self.mode!="elder" else min(1,.55*self.wisdom+.45*self.observation)

@dataclass
class Observer:
    kind:str; alerts:int=0; pressure:float=0.
    def observe(self,field):
        alert=(field.charge>.82 or field.structural<.73) if self.kind=="external" else (field.depth>7 or field.lattice<.72)
        if alert: self.alerts+=1; self.pressure=min(1,self.pressure+.08)
        else: self.pressure=max(0,self.pressure-.025)
        return alert

@dataclass
class Lineage:
    density:float=0.; feedback:float=0.; events:int=0
    def compress(self,fb):
        if fb>.12:
            self.events+=1; self.density=min(1,self.density*.9+fb*.14); self.feedback=min(1,self.feedback*.84+fb*.2)

@dataclass
class Archetype:
    resonance:float=0.; cycles:int=0
    def update(self,density,pattern):
        if pattern>.42:
            self.cycles+=1; self.resonance=min(1,self.resonance*.91+density*.06+pattern*.045)
        else: self.resonance*=.985

@dataclass
class Event:
    kind:str; intensity:float; novelty:float; contradiction:float

class Field:
    def __init__(self,seed=1):
        self.rng=random.Random(seed); self.bodies=self.make_bodies()
        self.generations=[Generation(12),Generation(38,wisdom=.28,observation=.24),Generation(54,wisdom=.42,observation=.36)]
        self.observers={"Alpha":Observer("external"),"Omega":Observer("temporal")}
        self.lineages={n:Lineage() for n in ["Origin","Form","Motion","Return"]}
        self.archetypes={n:Archetype() for n in ["Healer","Witness","Wanderer","Sovereign","Bridge","Betrayer","Martyr","Child"]}
        self.cycle=0; self.structural=.84; self.vitality=.74; self.viability=.74; self.charge=.6; self.lattice=.86; self.depth=0
        self.closures=0; self.recursions=0; self.suspicious=0; self.dream=0; self.rem=0; self.heal=0; self.renew=0; self.variants=0; self.unknowns=0; self.decay=0
    def make_bodies(self):
        rows=[(1,"Light King","primary","light"),(2,"Shadow Queen","primary","shadow"),(3,"Mercury","primary","mercury"),(4,"Core","core","core")]
        idx=5
        for d in ["Health","Finance","Legal","Language","Memory","Strategy","Ethics","Emotion","Infrastructure","Discovery","Governance","Creation"]:
            rows.append((idx,d+"-Light","domain","light")); idx+=1
            rows.append((idx,d+"-Shadow","domain","shadow")); idx+=1
        for t in ["Healer","Builder","Warrior","Scholar","Trader","Mystic","Witness","Keeper"]:
            rows.append((idx,t,"tribe","temperament")); idx+=1
        for a in ["Origin","Form","Motion","Return"]:
            rows.append((idx,a,"ancestor","meta")); idx+=1
        return {i:Body(i,n,c,s,.6+self.rng.random()*.16) for i,n,c,s in rows}
    def active(self,e):
        vals=list(self.bodies.values()); core=[b for b in vals if b.cls in ("primary","core")]
        if e.kind=="normal": chosen=[b for b in vals if b.cls in ("domain","tribe") and b.id%3==0][:10]
        elif e.kind=="stress": chosen=[b for b in vals if b.cls in ("domain","tribe") and b.id%2==0][:18]
        elif e.kind=="extreme": chosen=[b for b in vals if b.cls in ("domain","ancestor")]
        elif e.kind=="contradiction": chosen=[b for b in vals if b.side in ("light","shadow","mercury")]
        elif e.kind=="drift": chosen=[b for b in vals if b.cls in ("tribe","ancestor") or "Memory" in b.name]
        else: chosen=vals
        return list({b.id:b for b in core+chosen}.values())
    def group_signal(self,side,e,pressure):
        g=[b for b in self.bodies.values() if b.side==side]
        return statistics.mean(b.signal(self.rng,e.intensity,pressure,e.contradiction) for b in g)
    def threshold(self,e):
        return max(.055,.125-.035*e.intensity-.03*e.novelty-.02*abs(e.contradiction))
    def damp(self):
        return .68 if self.charge>=.86 else .8 if self.charge>=.78 else .93 if self.charge>=.62 else 1
    def elder_feedback(self):
        if self.cycle%12==0:
            for g in self.generations: g.step()
        vals=[g.feedback() for g in self.generations if g.mode=="elder"]
        fb=statistics.mean(vals) if vals else 0
        for lin in self.lineages.values(): lin.compress(fb)
        return fb
    def myth(self,pattern):
        dens=statistics.mean(l.density for l in self.lineages.values())
        for a in self.archetypes.values(): a.update(dens,pattern)
    def maybe_renew(self,e,fb):
        pressure=e.novelty+fb+max(0,.78-self.lattice)
        if pressure>.86 and self.rng.random()<.32:
            self.renew+=1; self.variants+=1
            new_id=max(self.bodies)+1
            name,cls,side=self.rng.choice([("Adaptive Healer","tribe","temperament"),("Bridge Builder","tribe","temperament"),("Dream Cartographer","tribe","temperament"),("Storm Sentinel","tribe","temperament")])
            self.bodies[new_id]=Body(new_id,f"{name}-{self.variants}",cls,side,.56)
    def recovery(self,active):
        if self.charge<.67:
            self.dream+=1
            for b in active: b.recover(.017)
            self.lattice=min(1,self.lattice+.005); self.charge=max(0,self.charge-.01)
        if self.charge<.61: self.rem+=1; self.vitality=min(1,self.vitality+.003)
        if self.depth<=2 and self.charge<.64:
            self.heal+=1
            for b in self.bodies.values(): b.recover(.005)
    def step(self,e):
        self.cycle+=1; pressure=statistics.mean(o.pressure for o in self.observers.values()); active=self.active(e)
        l=self.group_signal("light",e,pressure); s=self.group_signal("shadow",e,pressure); m=self.group_signal("mercury",e,pressure)
        if e.kind=="unknown":
            self.unknowns+=1; m=min(1,m+e.novelty*.1); s=max(0,s-e.novelty*.05); l=min(1,l+e.contradiction*.04)
        th=self.threshold(e); pairs=[abs(l-s)<=th,abs(l-m)<=th,abs(s-m)<=th]; agree=sum(pairs); spread=max(l,s,m)-min(l,s,m); perfect=all(pairs)
        if agree>=1:
            self.closures+=1; dec=(.026 if perfect else .016)*self.damp(); self.decay=min(1,self.decay*.92+dec)
            if perfect and spread<.035: self.suspicious+=1; self.vitality+=.005; self.structural-=.004
            else: self.structural+=.005*self.damp(); self.viability+=.003
            self.depth=max(0,self.depth-1)
            for b in active: b.close(dec)
            action="close"
        else:
            self.recursions+=1; self.depth+=1; self.charge+=.035*e.intensity*self.damp(); self.vitality+=.017*e.intensity; self.structural-=.014*e.intensity
            for b in active: b.recurse(e.intensity)
            action="recurse"
        aa=self.observers["Alpha"].observe(self); oo=self.observers["Omega"].observe(self)
        fb=self.elder_feedback(); pattern=max(0,1-spread*3); self.myth(pattern); self.maybe_renew(e,fb); self.recovery(active)
        trust=statistics.mean(b.trust for b in self.bodies.values()); fatigue=statistics.mean(b.fatigue for b in self.bodies.values())
        lin=statistics.mean(lin.density for lin in self.lineages.values()); arch=statistics.mean(a.resonance for a in self.archetypes.values())
        self.lattice+=(trust-fatigue*.12+lin*.05+arch*.04-self.lattice)*.05
        self.charge+=(.58+e.intensity*.12+spread*.28-self.charge)*.05
        self.structural+=(.835+lin*.04-e.intensity*.03-self.structural)*.03
        self.vitality+=(.73+e.intensity*.07+e.novelty*.03-self.vitality)*.03
        self.viability=self.structural*(.55+.45*self.vitality)+self.lattice*.08-self.depth*.006
        self.structural=max(0,min(1,self.structural)); self.vitality=max(0,min(1,self.vitality)); self.viability=max(0,min(1,self.viability)); self.charge=max(0,min(1,self.charge)); self.lattice=max(0,min(1,self.lattice))
        return {"cycle":self.cycle,"event":e.kind,"action":action,"bodies":len(self.bodies),"active_bodies":len(active),"light":round(l,6),"shadow":round(s,6),"mercury":round(m,6),"threshold":round(th,6),"agreements":agree,"spread":round(spread,6),"structural_stability":round(self.structural,6),"vitality":round(self.vitality,6),"viability":round(self.viability,6),"field_charge":round(self.charge,6),"lattice_coherence":round(self.lattice,6),"recursion_depth":self.depth,"confidence_decay":round(self.decay,6),"avg_trust":round(trust,6),"avg_fatigue":round(fatigue,6),"lineage_density":round(lin,6),"archetype_resonance":round(arch,6),"elder_feedback":round(fb,6),"closures":self.closures,"recursions":self.recursions,"suspicious_closures":self.suspicious,"dream_cycles":self.dream,"rem_cycles":self.rem,"healing_cycles":self.heal,"renewal_cycles":self.renew,"new_variants":self.variants,"unknown_events":self.unknowns,"alpha_alerts":self.observers["Alpha"].alerts,"omega_alerts":self.observers["Omega"].alerts,"alpha_alert":aa,"omega_alert":oo}

def stream(mode,cycles):
    events=[]
    for t in range(cycles):
        if mode=="normal": events.append(Event("normal",.4,.05,.05*math.sin(t*.05)))
        elif mode=="stress": events.append(Event("stress",min(1,.45+t/cycles*.55),.1,.25*math.sin(t*.08)))
        elif mode=="extreme":
            k="unknown" if t%29==0 else "extreme"; events.append(Event(k,min(1.35,.7+t/cycles*.75),.45 if k=="unknown" else .18,.55*math.sin(t*.13)))
        elif mode=="contradiction": events.append(Event("contradiction",.78+.18*math.sin(t*.1),.2,.85*math.sin(t*.17)))
        elif mode=="drift":
            k="unknown" if t%43==0 else "drift"; events.append(Event(k,min(1.15,.35+t/cycles*.8),.35 if k=="unknown" else .12,.35*math.sin(t*.035)))
    return events

def run(mode,cycles,outdir):
    f=Field(1100+sum(ord(c) for c in mode)); rows=[f.step(e) for e in stream(mode,cycles)]
    with (Path(outdir)/f"run_{mode}.csv").open("w",newline="") as fh:
        w=csv.DictWriter(fh,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    def avg(k): return sum(float(r[k]) for r in rows)/len(rows)
    return {"mode":mode,"cycles":cycles,"final_bodies":rows[-1]["bodies"],"avg_structural_stability":round(avg("structural_stability"),6),"min_structural_stability":round(min(float(r["structural_stability"]) for r in rows),6),"avg_vitality":round(avg("vitality"),6),"avg_viability":round(avg("viability"),6),"avg_field_charge":round(avg("field_charge"),6),"max_field_charge":round(max(float(r["field_charge"]) for r in rows),6),"avg_lattice_coherence":round(avg("lattice_coherence"),6),"max_recursion_depth":max(int(r["recursion_depth"]) for r in rows),"closures":rows[-1]["closures"],"recursions":rows[-1]["recursions"],"suspicious_closures":rows[-1]["suspicious_closures"],"dream_cycles":rows[-1]["dream_cycles"],"rem_cycles":rows[-1]["rem_cycles"],"healing_cycles":rows[-1]["healing_cycles"],"new_variants":rows[-1]["new_variants"],"unknown_events":rows[-1]["unknown_events"],"alpha_alerts":rows[-1]["alpha_alerts"],"omega_alerts":rows[-1]["omega_alerts"],"avg_lineage_density":round(avg("lineage_density"),6),"avg_archetype_resonance":round(avg("archetype_resonance"),6)}

def run_all(outdir="runs",cycles=420):
    outdir=Path(outdir); outdir.mkdir(parents=True,exist_ok=True)
    summaries=[run(m,cycles,outdir) for m in ["normal","stress","extreme","contradiction","drift"]]
    with (outdir/"summary.csv").open("w",newline="") as fh:
        w=csv.DictWriter(fh,fieldnames=list(summaries[0].keys())); w.writeheader(); w.writerows(summaries)
    with (outdir/"summary.json").open("w") as fh: json.dump(summaries,fh,indent=2)
    return summaries

if __name__=="__main__":
    print(json.dumps(run_all("runs",420),indent=2))
