
import json, hashlib, sqlite3, time, zipfile
from pathlib import Path

def digest(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, default=str).encode()).hexdigest()

class Wallet:
    def __init__(self, path="wallet.db", owner="citizen:local"):
        self.owner=owner
        self.conn=sqlite3.connect(Path(path)); self.conn.row_factory=sqlite3.Row
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS owner(id TEXT PRIMARY KEY,name TEXT,domain TEXT,status TEXT,trust REAL,meta TEXT);
        CREATE TABLE IF NOT EXISTS creds(id TEXT PRIMARY KEY,owner TEXT,type TEXT,issuer TEXT,status TEXT,proof TEXT,trust REAL,issued REAL,expires REAL,meta TEXT);
        CREATE TABLE IF NOT EXISTS proofs(id TEXT PRIMARY KEY,cred TEXT,type TEXT,proof TEXT,status TEXT,details TEXT,created REAL);
        CREATE TABLE IF NOT EXISTS revocations(id INTEGER PRIMARY KEY,ts REAL,cred TEXT,source TEXT,status TEXT,details TEXT);
        CREATE TABLE IF NOT EXISTS presentations(id TEXT PRIMARY KEY,ts REAL,audience TEXT,creds TEXT,proof TEXT,status TEXT,details TEXT);
        CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,ts REAL,type TEXT,subject TEXT,details TEXT);
        CREATE TABLE IF NOT EXISTS ledger(seq INTEGER PRIMARY KEY AUTOINCREMENT,kind TEXT,subject TEXT,payload_hash TEXT,prev_hash TEXT,entry_hash TEXT);
        """); self.conn.commit()
    def last_hash(self):
        r=self.conn.execute("SELECT entry_hash FROM ledger ORDER BY seq DESC LIMIT 1").fetchone()
        return r["entry_hash"] if r else "GENESIS"
    def receipt(self,k,s,p):
        prev=self.last_hash(); ph=digest(p); eh=digest({"kind":k,"subject":s,"payload_hash":ph,"prev_hash":prev})
        self.conn.execute("INSERT INTO ledger(kind,subject,payload_hash,prev_hash,entry_hash) VALUES(?,?,?,?,?)",(k,s,ph,prev,eh)); self.conn.commit()
    def event(self,t,s,d=None):
        self.conn.execute("INSERT INTO events(ts,type,subject,details) VALUES(?,?,?,?)",(time.time(),t,s,json.dumps(d or {},default=str)))
        self.receipt("event",s,{"type":t,"details":d or {}})
    def verify_ledger(self):
        prev="GENESIS"; n=0
        for r in self.conn.execute("SELECT seq,kind,subject,payload_hash,prev_hash,entry_hash FROM ledger ORDER BY seq"):
            exp=digest({"kind":r["kind"],"subject":r["subject"],"payload_hash":r["payload_hash"],"prev_hash":prev})
            if r["prev_hash"]!=prev: return {"ok":False,"seq":r["seq"],"reason":"prev_hash_mismatch"}
            if r["entry_hash"]!=exp: return {"ok":False,"seq":r["seq"],"reason":"entry_hash_mismatch"}
            prev=r["entry_hash"]; n+=1
        return {"ok":True,"entries":n,"head":prev}
    def init(self,name,domain="carbon",trust=50,meta=None):
        self.conn.execute("INSERT OR REPLACE INTO owner VALUES(?,?,?,?,?,?)",(self.owner,name,domain,"active",float(trust),json.dumps(meta or {})))
        self.event("wallet_initialized",self.owner,{"name":name,"domain":domain,"trust":trust}); self.conn.commit()
        return {"owner":self.owner,"name":name,"domain":domain,"trust":trust}
    def import_credential(self,cid,typ,issuer,status="active",proof="",trust=50,ttl=365,meta=None):
        now=time.time(); exp=now+ttl*86400 if ttl else 0
        self.conn.execute("INSERT OR REPLACE INTO creds VALUES(?,?,?,?,?,?,?,?,?,?)",(cid,self.owner,typ,issuer,status,proof,float(trust),now,exp,json.dumps(meta or {})))
        self.event("credential_imported",cid,{"type":typ,"issuer":issuer,"status":status,"trust":trust}); self.conn.commit()
        return {"credential":cid,"status":status,"trust":trust}
    def add_proof(self,cid,typ,details=None):
        details=details or {}; ph=digest({"cred":cid,"type":typ,"details":details}); pid="proof:"+ph[:16]
        self.conn.execute("INSERT OR REPLACE INTO proofs VALUES(?,?,?,?,?,?,?)",(pid,cid,typ,ph,"active",json.dumps(details),time.time()))
        self.event("proof_added",pid,{"credential":cid,"type":typ}); self.conn.commit()
        return {"proof":pid,"hash":ph}
    def revoke_check(self,cid,source="local",revoked=False,details=None):
        status="revoked" if revoked else "clear"
        self.conn.execute("INSERT INTO revocations(ts,cred,source,status,details) VALUES(?,?,?,?,?)",(time.time(),cid,source,status,json.dumps(details or {})))
        if revoked: self.conn.execute("UPDATE creds SET status='revoked' WHERE id=?",(cid,))
        self.event("revocation_check",cid,{"source":source,"status":status}); self.conn.commit()
        return {"credential":cid,"status":status}
    def cred(self,cid):
        r=self.conn.execute("SELECT * FROM creds WHERE id=?",(cid,)).fetchone()
        return dict(r) if r else None
    def credentials(self):
        return [dict(r) for r in self.conn.execute("SELECT id,type,issuer,status,proof,trust,expires FROM creds ORDER BY id")]
    def gate(self,cids,minimum=60):
        out=[]
        for cid in cids:
            c=self.cred(cid)
            if not c: out.append({"credential":cid,"allowed":False,"reason":"missing"}); continue
            if c["status"]!="active": out.append({"credential":cid,"allowed":False,"reason":"not_active"}); continue
            if c["expires"] and c["expires"]<time.time(): out.append({"credential":cid,"allowed":False,"reason":"expired"}); continue
            if float(c["trust"])<minimum: out.append({"credential":cid,"allowed":False,"reason":"low_trust","trust":c["trust"]}); continue
            out.append({"credential":cid,"allowed":True,"trust":c["trust"]})
        return {"allowed":all(x["allowed"] for x in out),"results":out}
    def present(self,audience,cids,minimum=60,details=None):
        g=self.gate(cids,minimum); payload={"owner":self.owner,"audience":audience,"credentials":cids,"gate":g,"details":details or {}}
        ph=digest(payload); pid="presentation:"+ph[:16]; status="ready" if g["allowed"] else "blocked"
        self.conn.execute("INSERT OR REPLACE INTO presentations VALUES(?,?,?,?,?,?,?)",(pid,time.time(),audience,json.dumps(cids),ph,status,json.dumps(payload,default=str)))
        self.event("presentation_created",pid,{"audience":audience,"status":status}); self.conn.commit()
        return {"presentation":pid,"status":status,"proof":ph,"gate":g}
    def summary(self):
        owner=self.conn.execute("SELECT * FROM owner WHERE id=?",(self.owner,)).fetchone()
        creds=self.credentials(); active=[c for c in creds if c["status"]=="active"]; revoked=[c for c in creds if c["status"]=="revoked"]
        avg=round(sum(float(c["trust"]) for c in creds)/max(1,len(creds)),2)
        return {"owner":dict(owner) if owner else None,"credential_count":len(creds),"active":len(active),"revoked":len(revoked),"avg_trust":avg,"ledger":self.verify_ledger()}
    def stats(self):
        return {"owner":self.owner,"credentials":self.conn.execute("SELECT COUNT(*) n FROM creds").fetchone()["n"],"proofs":self.conn.execute("SELECT COUNT(*) n FROM proofs").fetchone()["n"],"revocation_checks":self.conn.execute("SELECT COUNT(*) n FROM revocations").fetchone()["n"],"presentations":self.conn.execute("SELECT COUNT(*) n FROM presentations").fetchone()["n"],"events":self.conn.execute("SELECT COUNT(*) n FROM events").fetchone()["n"],"ledger":self.verify_ledger(),"db_integrity":self.conn.execute("PRAGMA integrity_check").fetchone()[0]}
    def bundle(self,out):
        out=Path(out)
        with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as z:
            for t in ["owner","creds","proofs","revocations","presentations","events","ledger"]:
                z.writestr(f"{t}.json",json.dumps([dict(r) for r in self.conn.execute(f"SELECT * FROM {t} ORDER BY 1")],indent=2,default=str))
            z.writestr("wallet_summary.json",json.dumps(self.summary(),indent=2,default=str))
            z.writestr("manifest.json",json.dumps({"stats":self.stats(),"created":time.time()},indent=2))
        return {"bundle":str(out),"exists":out.exists()}
def seed_demo(w):
    w.init("Root User","carbon",88)
    w.import_credential("credential:license:C-1","license","north","active","proof-license",92,365)
    w.import_credential("credential:id:C-2","state_id","north","active","proof-id",85,365)
    w.import_credential("credential:old:C-0","old_license","south","revoked","proof-old",20,0)
    w.add_proof("credential:license:C-1","address_proof",{"state":"MN"})
    w.add_proof("credential:id:C-2","identity_proof",{"method":"document"})
    w.revoke_check("credential:license:C-1","north",False)
    ready=w.present("law_enforcement",["credential:license:C-1","credential:id:C-2"],60)
    blocked=w.present("high_trust_check",["credential:old:C-0"],60)
    return {"ready":ready,"blocked":blocked,"summary":w.summary()}
