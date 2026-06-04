
from dataclasses import dataclass
from pathlib import Path
import random, math, statistics, csv, json

@dataclass
class Body:
    id:int; name:str; cls:str; side:str; trust:float=.7; fatigue:float=0; charge:float=0; active:bool=True
    def signal(self,rng,stress,pressure):
        base={'light':.57,'shadow':.47,'mercury':.52,'core':.50,'temperament':.51,'meta':.50}.get(self.side,.5)
        return max(0,min(1,base+rng.gauss(0,.035+.02*stress)+(self.trust-.5)*.08-self.fatigue*.04-pressure*.02))
    def close(self,decay):
        self.trust=max(.2,min(.94,self.trust+.004-decay*.04)); self.fatigue=min(1,self.fatigue+decay*.55); self.charge*=.92
    def recurse(self,stress):
        self.trust=max(.2,self.trust-.006*stress); self.fatigue=min(1,self.fatigue+.025*stress); self.charge=min(1,self.charge+.03*stress)
    def recover(self,a):
        self.fatigue=max(0,self.fatigue-a); self.trust=min(.94,self.trust+a*.25); self.charge=max(0,self.charge-a*.2)

@dataclass
class Generation:
    id:int; age:int; body_ids:list; agency:float=1; mode:str='active'; wisdom:float=0; observation:float=0
    def step_age(self):
        self.age+=1
        if self.age>=55 and self.mode=='active':
            self.mode='elder_observer'; self.agency=0; self.wisdom=min(1,self.wisdom+.25); self.observation=min(1,self.observation+.35)
    def feedback(self):
        return 0 if self.mode!='elder_observer' else min(1,.55*self.wisdom+.45*self.observation)

@dataclass
class Observer:
    name:str; kind:str; alerts:int=0; pressure:float=0
    def observe(self,field):
        alert = (field.charge>.82 or field.struct<.74) if self.kind=='external' else (field.depth>8 or field.lattice<.72)
        if alert: self.alerts+=1; self.pressure=min(1,self.pressure+.08)
        else: self.pressure=max(0,self.pressure-.025)
        return alert

@dataclass
class Lineage:
    name:str; density:float=0; feedback:float=0; events:int=0
    def compress(self,fb):
        if fb>.15:
            self.events+=1; self.density=min(1,self.density*.88+fb*.18); self.feedback=min(1,self.feedback*.82+fb*.22)

@dataclass
class Archetype:
    name:str; resonance:float=0; cycles:int=0
    def update(self,density,pattern):
        if pattern>.35: self.cycles+=1; self.resonance=min(1,self.resonance*.90+.08*density+.05*pattern)
        else: self.resonance*=.985

@dataclass
class Event:
    kind:str; intensity:float; novelty:float=0

class Field:
    def __init__(self,seed=1):
        self.rng=random.Random(seed); self.bodies={}; self._make_bodies()
        self.generations=[Generation(1,12,list(range(1,15)),wisdom=.15,observation=.1),Generation(2,38,list(range(15,29)),wisdom=.25,observation=.2),Generation(3,54,list(range(29,41)),wisdom=.4,observation=.35)]
        self.observers={'Alpha':Observer('Alpha','external'),'Omega':Observer('Omega','temporal')}
        self.lineages={n:Lineage(n) for n in ['Origin','Form','Motion','Return']}
        self.archetypes={n:Archetype(n) for n in ['Healer','Witness','Wanderer','Sovereign','Bridge','Betrayer','Martyr','Child']}
        self.cycle=0; self.struct=.84; self.vital=.74; self.viable=.74; self.charge=.60; self.lattice=.86; self.depth=0; self.decay=0
        self.closures=0; self.recursions=0; self.suspicious=0; self.dream=0; self.rem=0; self.heal=0; self.renewal=0; self.variants=0; self.unknown=0
    def _make_bodies(self):
        rows=[(1,'Light King','primary_attractor','light'),(2,'Shadow Queen','primary_attractor','shadow'),(3,'Mercury','primary_attractor','mercury'),(4,'Core Resolver','core','core')]
        domains='Health Finance Legal Language Memory Strategy Ethics Emotion Infrastructure Discovery Governance Creation'.split(); i=5
        for d in domains:
            rows.append((i,f'{d}-Light','domain','light')); i+=1; rows.append((i,f'{d}-Shadow','domain','shadow')); i+=1
        for t in 'Healer Builder Warrior Scholar Trader Mystic Witness Keeper'.split(): rows.append((i,t,'tribe','temperament')); i+=1
        for a in 'Origin Form Motion Return'.split(): rows.append((i,a,'ancestor','meta')); i+=1
        for bid,name,cls,side in rows: self.bodies[bid]=Body(bid,name,cls,side,.62+self.rng.random()*.16)
    def sig(self,side,stress,pressure):
        g=[b for b in self.bodies.values() if b.side==side and b.active]
        return statistics.mean([b.signal(self.rng,stress,pressure) for b in g]) if g else .5
    def active(self,e):
        base=[b for b in self.bodies.values() if b.cls in ('primary_attractor','core')]
        if e.kind=='normal': chosen=[b for b in self.bodies.values() if b.cls in ('domain','tribe') and b.id%3==0][:10]
        elif e.kind=='stress': chosen=[b for b in self.bodies.values() if b.cls in ('domain','tribe') and b.id%2==0][:18]
        elif e.kind=='extreme': chosen=[b for b in self.bodies.values() if b.cls in ('domain','ancestor')]
        elif e.kind=='contradiction': chosen=[b for b in self.bodies.values() if b.side in ('light','shadow','mercury')]
        elif e.kind=='drift': chosen=[b for b in self.bodies.values() if b.cls in ('tribe','ancestor') or 'Memory' in b.name]
        else: chosen=list(self.bodies.values())
        return list({b.id:b for b in base+chosen}.values())
    def damp(self):
        return .68 if self.charge>=.86 else .80 if self.charge>=.78 else .93 if self.charge>=.62 else 1
    def step(self,e):
        self.cycle+=1; pressure=sum(o.pressure for o in self.observers.values())/2; act=self.active(e)
        light=self.sig('light',e.intensity,pressure); shadow=self.sig('shadow',e.intensity,pressure); mercury=self.sig('mercury',e.intensity,pressure)
        if e.kind=='unknown': self.unknown+=1; mercury=min(1,mercury+e.novelty*.08); shadow=max(0,shadow-e.novelty*.04)
        pairs=[abs(light-shadow)<=.115,abs(light-mercury)<=.115,abs(shadow-mercury)<=.115]; agreements=sum(pairs); spread=max(light,shadow,mercury)-min(light,shadow,mercury); perfect=all(pairs); damp=self.damp()
        if agreements>=1:
            self.closures+=1; decay=(.022 if perfect else .014)*damp; self.decay=min(1,self.decay*.92+decay); self.depth=max(0,self.depth-1)
            if perfect and spread<.04: self.suspicious+=1; self.vital+=.006; self.struct-=.004
            else: self.struct+=.006*damp; self.viable+=.004
            for b in act: b.close(decay)
        else:
            self.recursions+=1; self.depth+=1; self.charge+=.025*e.intensity*damp; self.vital+=.015*e.intensity; self.struct-=.012*e.intensity
            for b in act: b.recurse(e.intensity)
        alpha=self.observers['Alpha'].observe(self); omega=self.observers['Omega'].observe(self)
        elder=[]
        for g in self.generations:
            if self.cycle%12==0: g.step_age()
            elder.append(g.feedback())
        fb=statistics.mean([x for x in elder if x>0]) if any(x>0 for x in elder) else 0
        for l in self.lineages.values(): l.compress(fb)
        density=statistics.mean(l.density for l in self.lineages.values()); pattern=max(0,1-spread*3)
        for a in self.archetypes.values(): a.update(density,pattern)
        if e.novelty+fb+max(0,.8-self.lattice)>.90 and self.rng.random()<.35:
            self.renewal+=1; self.variants+=1; nid=max(self.bodies)+1; name=self.rng.choice(['Adaptive Healer','Bridge Builder','Dream Cartographer','Storm Sentinel']); self.bodies[nid]=Body(nid,f'{name}-{self.variants}','tribe','temperament',.58)
        if self.charge<.67:
            self.dream+=1; [b.recover(.018) for b in act]; self.lattice=min(1,self.lattice+.006); self.charge=max(0,self.charge-.012)
        if self.charge<.61: self.rem+=1; self.vital=min(1,self.vital+.003)
        if self.depth<=2 and self.charge<.64:
            self.heal+=1; [b.recover(.006) for b in self.bodies.values()]
        avg_trust=statistics.mean(b.trust for b in self.bodies.values()); avg_fatigue=statistics.mean(b.fatigue for b in self.bodies.values()); arche=statistics.mean(a.resonance for a in self.archetypes.values())
        self.lattice+=(avg_trust-avg_fatigue*.12+density*.05+arche*.04-self.lattice)*.05
        self.charge+=(.58+e.intensity*.12+spread*.25-self.charge)*.05
        self.struct+=(.84+density*.04-e.intensity*.025-self.struct)*.03
        self.vital+=(.73+e.intensity*.07+e.novelty*.03-self.vital)*.03
        self.viable=self.struct*(.55+.45*self.vital)+self.lattice*.08-self.depth*.005
        for attr in ['struct','vital','viable','charge','lattice']: setattr(self,attr,max(0,min(1,getattr(self,attr))))
        return {'cycle':self.cycle,'event':e.kind,'bodies':len(self.bodies),'active_bodies':len(act),'light':round(light,6),'shadow':round(shadow,6),'mercury':round(mercury,6),'agreements':agreements,'spread':round(spread,6),'structural_stability':round(self.struct,6),'vitality':round(self.vital,6),'viability':round(self.viable,6),'field_charge':round(self.charge,6),'lattice_coherence':round(self.lattice,6),'recursion_depth':self.depth,'confidence_decay':round(self.decay,6),'avg_trust':round(avg_trust,6),'avg_fatigue':round(avg_fatigue,6),'lineage_density':round(density,6),'archetype_resonance':round(arche,6),'elder_feedback':round(fb,6),'closures':self.closures,'recursions':self.recursions,'suspicious_closures':self.suspicious,'dream_cycles':self.dream,'rem_cycles':self.rem,'healing_cycles':self.heal,'renewal_cycles':self.renewal,'new_variants':self.variants,'unknown_events':self.unknown,'alpha_alerts':self.observers['Alpha'].alerts,'omega_alerts':self.observers['Omega'].alerts,'alpha_alert':alpha,'omega_alert':omega}

def events(mode,cycles):
    out=[]
    for t in range(cycles):
        if mode=='normal': out.append(Event('normal',.40,.05))
        elif mode=='stress': out.append(Event('stress',min(1,.45+t/cycles*.55),.10))
        elif mode=='extreme':
            k='unknown' if t%37==0 else 'extreme'; out.append(Event(k,min(1.35,.70+t/cycles*.75),.40 if k=='unknown' else .18))
        elif mode=='contradiction': out.append(Event('contradiction',.78+.18*math.sin(t*.1),.20))
        elif mode=='drift':
            k='unknown' if t%53==0 else 'drift'; out.append(Event(k,min(1.15,.35+t/cycles*.80),.30 if k=='unknown' else .12))
    return out

def run_sim(mode,outdir,cycles=420):
    f=Field(1000+sum(map(ord,mode))); rows=[f.step(e) for e in events(mode,cycles)]
    p=Path(outdir)/f'run_{mode}.csv'
    with p.open('w',newline='') as fh:
        w=csv.DictWriter(fh,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    def avg(k): return sum(float(r[k]) for r in rows)/len(rows)
    return {'mode':mode,'cycles':cycles,'final_bodies':rows[-1]['bodies'],'avg_structural_stability':round(avg('structural_stability'),6),'min_structural_stability':round(min(float(r['structural_stability']) for r in rows),6),'avg_vitality':round(avg('vitality'),6),'avg_viability':round(avg('viability'),6),'avg_field_charge':round(avg('field_charge'),6),'max_field_charge':round(max(float(r['field_charge']) for r in rows),6),'avg_lattice_coherence':round(avg('lattice_coherence'),6),'max_recursion_depth':max(int(r['recursion_depth']) for r in rows),'closures':rows[-1]['closures'],'recursions':rows[-1]['recursions'],'suspicious_closures':rows[-1]['suspicious_closures'],'dream_cycles':rows[-1]['dream_cycles'],'rem_cycles':rows[-1]['rem_cycles'],'healing_cycles':rows[-1]['healing_cycles'],'new_variants':rows[-1]['new_variants'],'unknown_events':rows[-1]['unknown_events'],'alpha_alerts':rows[-1]['alpha_alerts'],'omega_alerts':rows[-1]['omega_alerts'],'avg_lineage_density':round(avg('lineage_density'),6),'avg_archetype_resonance':round(avg('archetype_resonance'),6)}

def run_all(outdir='runs',cycles=420):
    outdir=Path(outdir); outdir.mkdir(parents=True,exist_ok=True); modes=['normal','stress','extreme','contradiction','drift']; summaries=[run_sim(m,outdir,cycles) for m in modes]
    with (outdir/'summary.csv').open('w',newline='') as fh:
        w=csv.DictWriter(fh,fieldnames=list(summaries[0].keys())); w.writeheader(); w.writerows(summaries)
    (outdir/'summary.json').write_text(json.dumps(summaries,indent=2))
    return summaries

if __name__=='__main__': print(json.dumps(run_all(),indent=2))
