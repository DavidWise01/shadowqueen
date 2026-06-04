
import json,hashlib,sqlite3,time,zipfile
from pathlib import Path
def digest(o): return hashlib.sha256(json.dumps(o,sort_keys=True,default=str).encode()).hexdigest()
class Authority:
    def __init__(self,path="authority.db",domain="shadow-authority"):
        self.domain=domain
        self.conn=sqlite3.connect(Path(path)); self.conn.row_factory=sqlite3.Row
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS principals(id TEXT PRIMARY KEY,type TEXT,status TEXT,trust REAL,meta TEXT);
        CREATE TABLE IF NOT EXISTS grants(id TEXT PRIMARY KEY,grantor TEXT,grantee TEXT,scope TEXT,permissions TEXT,status TEXT,issued REAL,expires REAL,proof_hash TEXT,conditions TEXT,parent TEXT);
        CREATE TABLE IF NOT EXISTS decisions(id INTEGER PRIMARY KEY,ts REAL,principal TEXT,action TEXT,scope TEXT,allowed INTEGER,reason TEXT,grant_id TEXT,details TEXT);
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
    def add_principal(self,pid,ptype="carbon",trust=75,meta=None):
        self.conn.execute("INSERT OR REPLACE INTO principals VALUES(?,?,?,?,?)",(pid,ptype,"active",float(trust),json.dumps(meta or {})))
        self.event("principal_registered",pid,{"type":ptype,"trust":trust}); self.conn.commit()
        return {"principal":pid,"type":ptype,"trust":trust}
    def principal(self,pid):
        r=self.conn.execute("SELECT * FROM principals WHERE id=?",(pid,)).fetchone()
        return dict(r) if r else None
    def grant(self,grantor,grantee,scope,permissions,ttl=30,conditions=None,parent=""):
        if not self.principal(grantor): self.add_principal(grantor,"unknown",50)
        if not self.principal(grantee): self.add_principal(grantee,"unknown",50)
        issued=time.time(); expires=issued+ttl*86400 if ttl else 0
        payload={"grantor":grantor,"grantee":grantee,"scope":scope,"permissions":permissions,"issued":issued,"expires":expires,"conditions":conditions or {},"parent":parent}
        ph=digest(payload); gid="grant:"+ph[:16]
        self.conn.execute("INSERT OR REPLACE INTO grants VALUES(?,?,?,?,?,?,?,?,?,?,?)",(gid,grantor,grantee,scope,json.dumps(permissions),"active",issued,expires,ph,json.dumps(conditions or {}),parent))
        self.event("authority_granted",gid,payload); self.conn.commit()
        return {"grant":gid,"proof_hash":ph,"status":"active"}
    def revoke(self,gid,actor="system",reason="revoked"):
        self.conn.execute("UPDATE grants SET status='revoked' WHERE id=? OR parent=?",(gid,gid))
        self.event("authority_revoked",gid,{"actor":actor,"reason":reason}); self.conn.commit()
        return {"grant":gid,"status":"revoked"}
    def active_grants(self,principal):
        now=time.time()
        return [dict(r) for r in self.conn.execute("SELECT * FROM grants WHERE grantee=? AND status='active' AND (expires=0 OR expires>?)",(principal,now))]
    def record_decision(self,principal,action,scope,allowed,reason,gid="",details=None):
        self.conn.execute("INSERT INTO decisions(ts,principal,action,scope,allowed,reason,grant_id,details) VALUES(?,?,?,?,?,?,?,?)",(time.time(),principal,action,scope,1 if allowed else 0,reason,gid,json.dumps(details or {},default=str)))
        self.receipt("authority_decision",principal,{"action":action,"scope":scope,"allowed":allowed,"reason":reason,"grant":gid})
    def check(self,principal,action,scope,context=None):
        context=context or {}
        for g in self.active_grants(principal):
            perms=json.loads(g["permissions"]); cond=json.loads(g["conditions"] or "{}")
            if action not in perms and "*" not in perms: continue
            if g["scope"]!="*" and g["scope"]!=scope: continue
            p=self.principal(principal)
            if cond.get("min_trust") is not None and (not p or float(p["trust"])<float(cond["min_trust"])): continue
            if cond.get("requires_human") and context.get("actor_domain")=="silicon": continue
            self.record_decision(principal,action,scope,True,"grant_match",g["id"],{"conditions":cond})
            return {"allowed":True,"grant":g["id"],"reason":"grant_match"}
        self.record_decision(principal,action,scope,False,"no_active_matching_grant","",context)
        return {"allowed":False,"reason":"no_active_matching_grant"}
    def grants(self): return [dict(r) for r in self.conn.execute("SELECT id,grantor,grantee,scope,permissions,status,issued,expires,proof_hash,conditions,parent FROM grants ORDER BY issued")]
    def decisions(self): return [dict(r) for r in self.conn.execute("SELECT principal,action,scope,allowed,reason,grant_id,details FROM decisions ORDER BY id")]
    def proof(self,gid):
        g=self.conn.execute("SELECT * FROM grants WHERE id=?",(gid,)).fetchone()
        if not g: return {"ok":False,"reason":"missing_grant"}
        d=dict(g); return {"ok":True,"grant":d,"valid":d["status"]=="active" and (d["expires"]==0 or d["expires"]>time.time())}
    def stats(self):
        return {"domain":self.domain,"principals":self.conn.execute("SELECT COUNT(*) n FROM principals").fetchone()["n"],"grants":self.conn.execute("SELECT COUNT(*) n FROM grants").fetchone()["n"],"decisions":self.conn.execute("SELECT COUNT(*) n FROM decisions").fetchone()["n"],"events":self.conn.execute("SELECT COUNT(*) n FROM events").fetchone()["n"],"ledger":self.verify_ledger(),"db_integrity":self.conn.execute("PRAGMA integrity_check").fetchone()[0]}
    def bundle(self,out):
        out=Path(out)
        with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as z:
            for t in ["principals","grants","decisions","events","ledger"]:
                z.writestr(f"{t}.json",json.dumps([dict(r) for r in self.conn.execute(f"SELECT * FROM {t} ORDER BY 1")],indent=2,default=str))
            z.writestr("manifest.json",json.dumps({"stats":self.stats(),"created":time.time()},indent=2))
        return {"bundle":str(out),"exists":out.exists()}
def seed_demo(a):
    a.add_principal("citizen:root","carbon",88)
    a.add_principal("agent:wallet","silicon",80)
    a.add_principal("office:north","office",90)
    g1=a.grant("citizen:root","agent:wallet","wallet:citizen:root",["read_credentials","create_presentation"],30,{"min_trust":60})
    allowed=a.check("agent:wallet","read_credentials","wallet:citizen:root",{"actor_domain":"silicon"})
    denied=a.check("agent:wallet","issue_credential","wallet:citizen:root",{"actor_domain":"silicon"})
    g2=a.grant("office:north","agent:wallet","case:review",["read_case"],7,{"requires_human":True})
    human_ok=a.check("agent:wallet","read_case","case:review",{"actor_domain":"carbon"})
    silicon_block=a.check("agent:wallet","read_case","case:review",{"actor_domain":"silicon"})
    a.revoke(g1["grant"],"citizen:root","test revocation")
    after_revoke=a.check("agent:wallet","read_credentials","wallet:citizen:root",{})
    return {"wallet_grant":g1,"case_grant":g2,"allowed":allowed,"denied":denied,"human_ok":human_ok,"silicon_block":silicon_block,"after_revoke":after_revoke}
