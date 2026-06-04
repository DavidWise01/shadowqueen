import json, hashlib, sqlite3, time, zipfile
from pathlib import Path

def digest(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, default=str).encode()).hexdigest()

class Store:
    def __init__(self, path="fraud.db", office="north"):
        self.office = office
        self.conn = sqlite3.connect(Path(path))
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS nodes(id TEXT PRIMARY KEY,type TEXT,office TEXT,hash TEXT,version INTEGER,attrs TEXT);
        CREATE TABLE IF NOT EXISTS edges(id INTEGER PRIMARY KEY,src TEXT,dst TEXT,rel TEXT,office TEXT,hash TEXT,version INTEGER,attrs TEXT);
        CREATE TABLE IF NOT EXISTS fraud_findings(id INTEGER PRIMARY KEY,ts REAL,subject TEXT,kind TEXT,severity TEXT,score REAL,details TEXT);
        CREATE TABLE IF NOT EXISTS risk_scores(subject TEXT PRIMARY KEY,score REAL,severity TEXT,reasons TEXT,updated_ts REAL);
        CREATE TABLE IF NOT EXISTS audits(id INTEGER PRIMARY KEY,ts REAL,auditor TEXT,result TEXT,details TEXT);
        CREATE TABLE IF NOT EXISTS ledger(seq INTEGER PRIMARY KEY AUTOINCREMENT,kind TEXT,subject TEXT,payload_hash TEXT,prev_hash TEXT,entry_hash TEXT);
        """)
        self.conn.commit()

    def last_hash(self):
        r=self.conn.execute("SELECT entry_hash FROM ledger ORDER BY seq DESC LIMIT 1").fetchone()
        return r["entry_hash"] if r else "GENESIS"

    def receipt(self, kind, subject, payload):
        prev=self.last_hash(); ph=digest(payload); eh=digest({"kind":kind,"subject":subject,"payload_hash":ph,"prev_hash":prev})
        self.conn.execute("INSERT INTO ledger(kind,subject,payload_hash,prev_hash,entry_hash) VALUES(?,?,?,?,?)",(kind,subject,ph,prev,eh))
        self.conn.commit()

    def verify_ledger(self):
        prev="GENESIS"; n=0
        for r in self.conn.execute("SELECT seq,kind,subject,payload_hash,prev_hash,entry_hash FROM ledger ORDER BY seq"):
            exp=digest({"kind":r["kind"],"subject":r["subject"],"payload_hash":r["payload_hash"],"prev_hash":prev})
            if r["prev_hash"]!=prev: return {"ok":False,"seq":r["seq"],"reason":"prev_hash_mismatch"}
            if r["entry_hash"]!=exp: return {"ok":False,"seq":r["seq"],"reason":"entry_hash_mismatch"}
            prev=r["entry_hash"]; n+=1
        return {"ok":True,"entries":n,"head":prev}

    def node_id(self, typ, key): return f"{typ}:{digest({'type':typ,'key':key})[:16]}"

    def add_node(self, typ, key, attrs=None, version=1):
        attrs=attrs or {}; nid=self.node_id(typ,key); nh=digest({"id":nid,"type":typ,"attrs":attrs,"version":version})
        self.conn.execute("INSERT OR REPLACE INTO nodes VALUES(?,?,?,?,?,?)",(nid,typ,self.office,nh,version,json.dumps(attrs)))
        self.receipt("node", nid, {"type":typ,"hash":nh}); return nid

    def add_edge(self, src, dst, rel, attrs=None, version=1):
        attrs=attrs or {}; eh=digest({"src":src,"dst":dst,"rel":rel,"attrs":attrs,"version":version})
        self.conn.execute("INSERT INTO edges(src,dst,rel,office,hash,version,attrs) VALUES(?,?,?,?,?,?,?)",(src,dst,rel,self.office,eh,version,json.dumps(attrs)))
        self.receipt("edge", f"{src}->{dst}", {"rel":rel,"hash":eh}); return eh

    def nodes(self, typ=None):
        rows=self.conn.execute("SELECT * FROM nodes WHERE type=? ORDER BY id",(typ,)) if typ else self.conn.execute("SELECT * FROM nodes ORDER BY id")
        return [dict(r) for r in rows]
    def edges(self): return [dict(r) for r in self.conn.execute("SELECT * FROM edges ORDER BY id")]

    def finding(self, subject, kind, severity, score, details):
        self.conn.execute("INSERT INTO fraud_findings(ts,subject,kind,severity,score,details) VALUES(?,?,?,?,?,?)",(time.time(),subject,kind,severity,score,json.dumps(details,default=str)))
        self.receipt("fraud_finding", subject, {"kind":kind,"severity":severity,"score":score})

    def score_subject(self, subject, points, reason, bucket):
        cur=self.conn.execute("SELECT score,reasons FROM risk_scores WHERE subject=?",(subject,)).fetchone()
        score=(float(cur["score"]) if cur else 0)+points; reasons=json.loads(cur["reasons"]) if cur else []
        score=min(100.0,score); reasons.append({"bucket":bucket,"reason":reason,"points":points})
        severity="critical" if score>=80 else "high" if score>=60 else "medium" if score>=30 else "low"
        self.conn.execute("INSERT OR REPLACE INTO risk_scores VALUES(?,?,?,?,?)",(subject,score,severity,json.dumps(reasons),time.time()))
        return {"subject":subject,"score":score,"severity":severity,"reasons":reasons}

    def risk_scores(self): return [dict(r) for r in self.conn.execute("SELECT subject,score,severity,reasons FROM risk_scores ORDER BY score DESC")]
    def findings(self): return [dict(r) for r in self.conn.execute("SELECT subject,kind,severity,score,details FROM fraud_findings ORDER BY score DESC,id")]

    def stats(self):
        return {"office":self.office,"nodes":self.conn.execute("SELECT COUNT(*) n FROM nodes").fetchone()["n"],"edges":self.conn.execute("SELECT COUNT(*) n FROM edges").fetchone()["n"],"findings":self.conn.execute("SELECT COUNT(*) n FROM fraud_findings").fetchone()["n"],"risk_scores":self.conn.execute("SELECT COUNT(*) n FROM risk_scores").fetchone()["n"],"audits":self.conn.execute("SELECT COUNT(*) n FROM audits").fetchone()["n"],"ledger":self.verify_ledger(),"db_integrity":self.conn.execute("PRAGMA integrity_check").fetchone()[0]}

    def audit(self, auditor="auditor"):
        risks=self.risk_scores(); critical=len([r for r in risks if r["severity"]=="critical"]); high=len([r for r in risks if r["severity"]=="high"])
        result="critical" if critical else "warning" if high else "pass"
        details={"critical":critical,"high":high,"risk_count":len(risks)}
        self.conn.execute("INSERT INTO audits(ts,auditor,result,details) VALUES(?,?,?,?)",(time.time(),auditor,result,json.dumps(details)))
        self.receipt("fraud_audit", auditor, details); self.conn.commit(); return {"result":result,"details":details}

    def bundle(self, out):
        out=Path(out)
        with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as z:
            for t in ["nodes","edges","fraud_findings","risk_scores","audits","ledger"]:
                z.writestr(f"{t}.json",json.dumps([dict(r) for r in self.conn.execute(f"SELECT * FROM {t} ORDER BY 1")],indent=2,default=str))
            z.writestr("manifest.json",json.dumps({"stats":self.stats(),"created":time.time()},indent=2))
        return {"bundle":str(out),"exists":out.exists()}

class FraudEngine:
    def __init__(self, store): self.store=store
    def attrs(self,node): return json.loads(node["attrs"] or "{}")
    def analyze(self):
        findings=[]
        findings += self.duplicate_identities(); findings += self.synthetic_identities(); findings += self.credential_stuffing(); findings += self.address_clusters(); findings += self.relationship_anomalies()
        self.store.conn.commit(); return {"findings":len(findings),"risk_scores":self.store.risk_scores()}
    def duplicate_identities(self):
        groups={}; out=[]
        for n in self.store.nodes("person"):
            a=self.attrs(n); key=digest({"name":a.get("name","").lower().strip(),"dob":a.get("dob",""),"domain":a.get("domain","")})
            groups.setdefault(key,[]).append(n)
        for key,items in groups.items():
            if len(items)>1:
                ids=[i["id"] for i in items]
                for node_id in ids:
                    self.store.finding(node_id,"possible_duplicate_identity","high",65,{"duplicate_group":ids})
                    self.store.score_subject(node_id,65,"same normalized name/dob/domain as another person node","identity")
                out.append({"kind":"possible_duplicate_identity","nodes":ids})
        return out
    def synthetic_identities(self):
        out=[]; incoming={}; outgoing={}
        for e in self.store.edges(): incoming.setdefault(e["dst"],[]).append(e); outgoing.setdefault(e["src"],[]).append(e)
        for n in self.store.nodes("person"):
            a=self.attrs(n); missing=[k for k in ["name","dob","domain"] if not a.get(k)]; degree=len(incoming.get(n["id"],[]))+len(outgoing.get(n["id"],[]))
            if missing or degree==0:
                score=min(100,40+10*len(missing)+(20 if degree==0 else 0)); sev="high" if score>=60 else "medium"; details={"missing_core_fields":missing,"degree":degree}
                self.store.finding(n["id"],"synthetic_identity_signal",sev,score,details); self.store.score_subject(n["id"],score,"missing core identity fields or no relationship edges","identity"); out.append({"node":n["id"],"details":details})
        return out
    def credential_stuffing(self):
        by_person={}; out=[]
        for e in self.store.edges():
            if e["rel"]=="holds": by_person.setdefault(e["src"],[]).append(e)
        for person,edges in by_person.items():
            if len(edges)>=4:
                score=min(100,25+len(edges)*10); details={"credential_edges":len(edges),"credential_nodes":[e["dst"] for e in edges]}
                self.store.finding(person,"credential_stuffing_signal","high",score,details); self.store.score_subject(person,score,"excessive credential relationships","credential"); out.append({"person":person,"count":len(edges)})
        return out
    def address_clusters(self):
        residents={}; out=[]
        for e in self.store.edges():
            if e["rel"] in {"resides_at","uses_address"}: residents.setdefault(e["dst"],set()).add(e["src"])
        for address,people in residents.items():
            if len(people)>=3:
                score=min(100,30+len(people)*12); details={"address_node":address,"people":sorted(people),"count":len(people)}
                self.store.finding(address,"suspicious_address_cluster","high",score,details); self.store.score_subject(address,score,"too many identities tied to same address","address")
                for p in people: self.store.score_subject(p,25,"associated with suspicious address cluster","relationship")
                out.append(details)
        return out
    def relationship_anomalies(self):
        out=[]; valid={"holds","resides_at","uses_contact","owns_vehicle","validated_by","issued_by","same_as","parent_of"}
        for e in self.store.edges():
            if e["rel"] not in valid:
                self.store.finding(e["src"],"unknown_relationship_type","medium",35,{"edge":e}); self.store.score_subject(e["src"],35,f"unknown relationship type {e['rel']}","relationship"); out.append({"edge":e})
            if e["src"]==e["dst"]:
                self.store.finding(e["src"],"self_loop_relationship","medium",40,{"edge":e}); self.store.score_subject(e["src"],40,"self-loop relationship edge","relationship"); out.append({"edge":e})
        return out
