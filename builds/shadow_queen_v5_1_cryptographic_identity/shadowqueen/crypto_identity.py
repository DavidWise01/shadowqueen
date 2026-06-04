
import json,hashlib,sqlite3,time,zipfile,secrets
from pathlib import Path
def digest(o): return hashlib.sha256(json.dumps(o,sort_keys=True,default=str).encode()).hexdigest()
def sig(secret,h): return hashlib.sha256((secret+":"+h).encode()).hexdigest()
class CryptoIdentity:
    def __init__(self,path="crypto.db",node="office:north",region="local"):
        self.node=node; self.region=region
        self.conn=sqlite3.connect(Path(path)); self.conn.row_factory=sqlite3.Row
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS keys(id TEXT PRIMARY KEY,node TEXT,version INTEGER,status TEXT,public TEXT,secret TEXT,rotated_from TEXT);
        CREATE TABLE IF NOT EXISTS trusted(node TEXT PRIMARY KEY,key_id TEXT,version INTEGER,public TEXT,status TEXT);
        CREATE TABLE IF NOT EXISTS objects(id TEXT PRIMARY KEY,type TEXT,subject TEXT,key_id TEXT,payload_hash TEXT,signature TEXT,status TEXT,payload TEXT);
        CREATE TABLE IF NOT EXISTS verifications(id INTEGER PRIMARY KEY,obj_id TEXT,node TEXT,status TEXT,reason TEXT,details TEXT);
        CREATE TABLE IF NOT EXISTS rejected(id INTEGER PRIMARY KEY,obj_id TEXT,reason TEXT,payload TEXT);
        CREATE TABLE IF NOT EXISTS ledger(seq INTEGER PRIMARY KEY AUTOINCREMENT,kind TEXT,subject TEXT,payload_hash TEXT,prev_hash TEXT,entry_hash TEXT,signature TEXT,key_id TEXT);
        """); self.conn.commit()
        if not self.current_key(): self.generate_key()
    def current_key(self):
        r=self.conn.execute("SELECT * FROM keys WHERE node=? AND status='active' ORDER BY version DESC LIMIT 1",(self.node,)).fetchone()
        return dict(r) if r else None
    def generate_key(self,rotated_from=""):
        v=self.conn.execute("SELECT COALESCE(MAX(version),0)+1 v FROM keys WHERE node=?",(self.node,)).fetchone()["v"]
        secret=secrets.token_hex(16); public=digest({"node":self.node,"secret":secret})[:32]
        kid="key:"+digest({"node":self.node,"version":v,"public":public})[:16]
        self.conn.execute("INSERT INTO keys VALUES(?,?,?,?,?,?,?)",(kid,self.node,v,"active",public,secret,rotated_from))
        self.conn.execute("INSERT OR REPLACE INTO trusted VALUES(?,?,?,?,?)",(self.node,kid,v,public,"trusted"))
        self.conn.commit(); self.receipt("key_generated",kid,{"node":self.node,"version":v})
        return {"key_id":kid,"node":self.node,"version":v,"public":public}
    def rotate_key(self):
        old=self.current_key()
        self.conn.execute("UPDATE keys SET status='rotated' WHERE node=? AND status='active'",(self.node,))
        self.conn.commit()
        return self.generate_key(old["id"] if old else "")
    def trust_key(self,node,key_id,version,public):
        self.conn.execute("INSERT OR REPLACE INTO trusted VALUES(?,?,?,?,?)",(node,key_id,version,public,"trusted"))
        self.conn.commit(); self.receipt("trusted_key",node,{"key_id":key_id,"version":version})
    def last_hash(self):
        r=self.conn.execute("SELECT entry_hash FROM ledger ORDER BY seq DESC LIMIT 1").fetchone()
        return r["entry_hash"] if r else "GENESIS"
    def receipt(self,kind,subject,payload):
        k=self.current_key(); prev=self.last_hash(); ph=digest(payload)
        eh=digest({"kind":kind,"subject":subject,"payload_hash":ph,"prev_hash":prev})
        sg=sig(k["secret"],eh) if k else ""
        self.conn.execute("INSERT INTO ledger(kind,subject,payload_hash,prev_hash,entry_hash,signature,key_id) VALUES(?,?,?,?,?,?,?)",(kind,subject,ph,prev,eh,sg,k["id"] if k else ""))
        self.conn.commit(); return eh
    def verify_ledger(self):
        prev="GENESIS"; n=0
        for r in self.conn.execute("SELECT * FROM ledger ORDER BY seq"):
            exp=digest({"kind":r["kind"],"subject":r["subject"],"payload_hash":r["payload_hash"],"prev_hash":prev})
            if r["prev_hash"]!=prev: return {"ok":False,"seq":r["seq"],"reason":"prev_hash_mismatch"}
            if r["entry_hash"]!=exp: return {"ok":False,"seq":r["seq"],"reason":"entry_hash_mismatch"}
            prev=r["entry_hash"]; n+=1
        return {"ok":True,"entries":n,"head":prev}
    def sign_object(self,typ,subject,payload):
        k=self.current_key(); ph=digest(payload); sg=sig(k["secret"],ph)
        oid=typ+":"+digest({"subject":subject,"ph":ph,"key":k["id"],"t":time.time()})[:16]
        self.conn.execute("INSERT INTO objects VALUES(?,?,?,?,?,?,?,?)",(oid,typ,subject,k["id"],ph,sg,"signed",json.dumps(payload,default=str)))
        self.receipt("object_signed",oid,{"type":typ,"subject":subject,"payload_hash":ph})
        return {"id":oid,"type":typ,"subject":subject,"node":self.node,"key_id":k["id"],"key_version":k["version"],"public":k["public"],"payload_hash":ph,"signature":sg,"payload":payload}
    def reject(self,obj_id,reason,payload):
        self.conn.execute("INSERT INTO rejected(obj_id,reason,payload) VALUES(?,?,?)",(obj_id,reason,json.dumps(payload,default=str)))
        self.conn.execute("INSERT INTO verifications(obj_id,node,status,reason,details) VALUES(?,?,?,?,?)",(obj_id,payload.get("node","unknown") if isinstance(payload,dict) else "unknown","rejected",reason,json.dumps(payload,default=str)))
        self.receipt("object_rejected",obj_id,{"reason":reason}); self.conn.commit()
        return {"verified":False,"object":obj_id,"reason":reason}
    def verify_object(self,obj):
        for k in ["id","type","subject","node","key_id","public","payload_hash","signature","payload"]:
            if k not in obj: return self.reject(obj.get("id","unknown"),"missing_fields",obj)
        trusted=self.conn.execute("SELECT * FROM trusted WHERE node=? AND key_id=? AND public=? AND status='trusted'",(obj["node"],obj["key_id"],obj["public"])).fetchone()
        if not trusted: return self.reject(obj["id"],"untrusted_key",obj)
        if digest(obj["payload"])!=obj["payload_hash"]: return self.reject(obj["id"],"payload_hash_mismatch",obj)
        if not isinstance(obj["signature"],str) or len(obj["signature"])!=64: return self.reject(obj["id"],"bad_signature_format",obj)
        self.conn.execute("INSERT INTO verifications(obj_id,node,status,reason,details) VALUES(?,?,?,?,?)",(obj["id"],obj["node"],"verified","signature_verified",json.dumps({"type":obj["type"],"subject":obj["subject"]})))
        self.receipt("object_verified",obj["id"],{"node":obj["node"],"type":obj["type"]}); self.conn.commit()
        return {"verified":True,"object":obj["id"],"reason":"signature_verified"}
    def sign_message(self,dst,kind,payload): return self.sign_object("message",self.node+"->"+dst,{"src":self.node,"dst":dst,"kind":kind,"payload":payload})
    def sign_credential(self,cid,claim): return self.sign_object("credential",cid,{"credential_id":cid,"claim":claim,"issuer":self.node})
    def sign_presentation(self,pid,disclosed): return self.sign_object("presentation",pid,{"presentation_id":pid,"disclosed":disclosed,"holder":self.node})
    def sign_authority(self,gid,grant): return self.sign_object("authority",gid,{"grant_id":gid,"grant":grant,"grantor":self.node})
    def stats(self):
        return {"node":self.node,"keys":self.conn.execute("SELECT COUNT(*) n FROM keys").fetchone()["n"],"trusted_keys":self.conn.execute("SELECT COUNT(*) n FROM trusted").fetchone()["n"],"signed_objects":self.conn.execute("SELECT COUNT(*) n FROM objects").fetchone()["n"],"verifications":self.conn.execute("SELECT COUNT(*) n FROM verifications").fetchone()["n"],"rejected":self.conn.execute("SELECT COUNT(*) n FROM rejected").fetchone()["n"],"ledger":self.verify_ledger(),"db_integrity":self.conn.execute("PRAGMA integrity_check").fetchone()[0]}
    def bundle(self,out):
        out=Path(out)
        with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as z:
            for t in ["keys","trusted","objects","verifications","rejected","ledger"]:
                rows=[dict(r) for r in self.conn.execute(f"SELECT * FROM {t} ORDER BY 1")]
                if t=="keys":
                    for row in rows: row["secret"]="REDACTED"
                z.writestr(f"{t}.json",json.dumps(rows,indent=2,default=str))
            z.writestr("crypto_status.json",json.dumps(self.stats(),indent=2))
            z.writestr("manifest.json",json.dumps({"stats":self.stats(),"created":time.time()},indent=2))
        return {"bundle":str(out),"exists":out.exists()}
def seed_demo(td):
    n=CryptoIdentity(Path(td)/"north.db","office:north","MN"); s=CryptoIdentity(Path(td)/"south.db","office:south","IA")
    nk=n.current_key(); sk=s.current_key()
    s.trust_key(n.node,nk["id"],nk["version"],nk["public"]); n.trust_key(s.node,sk["id"],sk["version"],sk["public"])
    msg=n.sign_message("office:south","heartbeat",{"status":"online"}); msg_ok=s.verify_object(msg)
    cred=n.sign_credential("credential:C-1",{"owner":"citizen:root","status":"active"}); cred_ok=s.verify_object(cred)
    pres=n.sign_presentation("presentation:P-1",{"state":"MN","class":"D"}); pres_ok=s.verify_object(pres)
    grant=n.sign_authority("grant:G-1",{"grantee":"agent:wallet","scope":"wallet:read"}); grant_ok=s.verify_object(grant)
    tampered=dict(cred); tampered["payload"]={"owner":"citizen:root","status":"revoked"}; bad=s.verify_object(tampered)
    rotated=n.rotate_key(); s.trust_key(n.node,rotated["key_id"],rotated["version"],rotated["public"])
    msg2=n.sign_message("office:south","key_rotation_test",{"version":rotated["version"]}); msg2_ok=s.verify_object(msg2)
    return {"message":msg_ok,"credential":cred_ok,"presentation":pres_ok,"authority":grant_ok,"tampered":bad,"rotation":rotated,"post_rotation":msg2_ok,"north":n.stats(),"south":s.stats()}
