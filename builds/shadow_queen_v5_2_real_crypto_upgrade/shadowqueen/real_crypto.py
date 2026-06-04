
import json,sqlite3,time,zipfile,base64
from pathlib import Path
from hashlib import sha256
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

def digest(o): return sha256(json.dumps(o,sort_keys=True,default=str).encode()).hexdigest()
def b64(b): return base64.b64encode(b).decode()
def ub64(s): return base64.b64decode(s.encode())

class RealCryptoNode:
    def __init__(self,path="real_crypto.db",node="office:north",key_dir="keys"):
        self.node=node; self.key_dir=Path(key_dir); self.key_dir.mkdir(parents=True,exist_ok=True)
        self.conn=sqlite3.connect(Path(path)); self.conn.row_factory=sqlite3.Row
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS keys(id TEXT PRIMARY KEY,node TEXT,version INTEGER,status TEXT,public_pem TEXT,private_path TEXT,rotated_from TEXT);
        CREATE TABLE IF NOT EXISTS trust(node TEXT PRIMARY KEY,key_id TEXT,version INTEGER,public_pem TEXT,status TEXT);
        CREATE TABLE IF NOT EXISTS revocations(id INTEGER PRIMARY KEY,node TEXT,key_id TEXT,reason TEXT,status TEXT);
        CREATE TABLE IF NOT EXISTS rotations(id INTEGER PRIMARY KEY,node TEXT,old_key TEXT,new_key TEXT,reason TEXT);
        CREATE TABLE IF NOT EXISTS envelopes(id TEXT PRIMARY KEY,src TEXT,dst TEXT,kind TEXT,payload_hash TEXT,signature TEXT,key_id TEXT,status TEXT,payload TEXT);
        CREATE TABLE IF NOT EXISTS verifications(id INTEGER PRIMARY KEY,envelope_id TEXT,src TEXT,status TEXT,reason TEXT);
        CREATE TABLE IF NOT EXISTS ledger(seq INTEGER PRIMARY KEY AUTOINCREMENT,kind TEXT,subject TEXT,payload_hash TEXT,prev_hash TEXT,entry_hash TEXT);
        """); self.conn.commit()
        if not self.current_key(): self.generate_key()
    def current_key(self):
        r=self.conn.execute("SELECT * FROM keys WHERE node=? AND status='active' ORDER BY version DESC LIMIT 1",(self.node,)).fetchone()
        return dict(r) if r else None
    def generate_key(self,rotated_from="",reason="initial"):
        priv=Ed25519PrivateKey.generate(); pub=priv.public_key()
        priv_pem=priv.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()).decode()
        pub_pem=pub.public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo).decode()
        v=self.conn.execute("SELECT COALESCE(MAX(version),0)+1 v FROM keys WHERE node=?",(self.node,)).fetchone()["v"]
        kid="ed25519:"+digest({"node":self.node,"v":v,"pub":pub_pem})[:16]
        path=self.key_dir/(kid.replace(":","_")+".pem"); path.write_text(priv_pem)
        self.conn.execute("INSERT INTO keys VALUES(?,?,?,?,?,?,?)",(kid,self.node,v,"active",pub_pem,str(path),rotated_from))
        self.conn.execute("INSERT OR REPLACE INTO trust VALUES(?,?,?,?,?)",(self.node,kid,v,pub_pem,"trusted"))
        if rotated_from: self.conn.execute("INSERT INTO rotations(node,old_key,new_key,reason) VALUES(?,?,?,?)",(self.node,rotated_from,kid,reason))
        self.conn.commit(); self.receipt("key_generated",kid,{"node":self.node,"version":v})
        return {"node":self.node,"key_id":kid,"version":v,"public_pem":pub_pem}
    def rotate_key(self,reason="scheduled"):
        old=self.current_key()
        self.conn.execute("UPDATE keys SET status='rotated' WHERE node=? AND status='active'",(self.node,))
        self.conn.commit(); return self.generate_key(old["id"] if old else "",reason)
    def private(self):
        return serialization.load_pem_private_key(Path(self.current_key()["private_path"]).read_bytes(),password=None)
    def public(self,pem): return serialization.load_pem_public_key(pem.encode())
    def export_public_key(self):
        k=self.current_key(); return {"node":self.node,"key_id":k["id"],"version":k["version"],"public_pem":k["public_pem"]}
    def import_public_key(self,b):
        self.conn.execute("INSERT OR REPLACE INTO trust VALUES(?,?,?,?,?)",(b["node"],b["key_id"],b["version"],b["public_pem"],"trusted"))
        self.conn.commit(); self.receipt("trust_import",b["node"],{"key_id":b["key_id"]})
    def revoke_key(self,node,key_id,reason="revoked"):
        self.conn.execute("UPDATE trust SET status='revoked' WHERE node=? AND key_id=?",(node,key_id))
        self.conn.execute("INSERT INTO revocations(node,key_id,reason,status) VALUES(?,?,?,?)",(node,key_id,reason,"active"))
        self.conn.commit(); self.receipt("key_revoked",key_id,{"node":node,"reason":reason})
    def last_hash(self):
        r=self.conn.execute("SELECT entry_hash FROM ledger ORDER BY seq DESC LIMIT 1").fetchone()
        return r["entry_hash"] if r else "GENESIS"
    def receipt(self,k,s,p):
        prev=self.last_hash(); ph=digest(p); eh=digest({"kind":k,"subject":s,"payload_hash":ph,"prev_hash":prev})
        self.conn.execute("INSERT INTO ledger(kind,subject,payload_hash,prev_hash,entry_hash) VALUES(?,?,?,?,?)",(k,s,ph,prev,eh)); self.conn.commit()
    def verify_ledger(self):
        prev="GENESIS"; n=0
        for r in self.conn.execute("SELECT * FROM ledger ORDER BY seq"):
            exp=digest({"kind":r["kind"],"subject":r["subject"],"payload_hash":r["payload_hash"],"prev_hash":prev})
            if r["prev_hash"]!=prev: return {"ok":False,"seq":r["seq"],"reason":"prev_hash_mismatch"}
            if r["entry_hash"]!=exp: return {"ok":False,"seq":r["seq"],"reason":"entry_hash_mismatch"}
            prev=r["entry_hash"]; n+=1
        return {"ok":True,"entries":n,"head":prev}
    def envelope(self,dst,kind,payload):
        k=self.current_key(); ph=digest(payload)
        body={"src":self.node,"dst":dst,"kind":kind,"payload_hash":ph,"key_id":k["id"],"key_version":k["version"],"created":time.time()}
        bh=digest(body); signature=b64(self.private().sign(bh.encode())); eid="env2:"+bh[:16]
        env={**body,"id":eid,"signature":signature,"payload":payload,"public_pem":k["public_pem"],"version":"envelope.v2"}
        self.conn.execute("INSERT OR REPLACE INTO envelopes VALUES(?,?,?,?,?,?,?,?,?)",(eid,self.node,dst,kind,ph,signature,k["id"],"signed",json.dumps(payload)))
        self.conn.commit(); self.receipt("envelope_signed",eid,{"kind":kind,"dst":dst})
        return env
    def verify_envelope(self,env):
        for f in ["id","src","dst","kind","payload_hash","key_id","created","signature","payload","public_pem","version"]:
            if f not in env: return self._ver(env.get("id","unknown"),env.get("src","unknown"),"rejected","missing:"+f)
        if env["version"]!="envelope.v2": return self._ver(env["id"],env["src"],"rejected","bad_version")
        t=self.conn.execute("SELECT * FROM trust WHERE node=? AND key_id=? AND public_pem=? AND status='trusted'",(env["src"],env["key_id"],env["public_pem"])).fetchone()
        if not t: return self._ver(env["id"],env["src"],"rejected","untrusted_or_revoked_key")
        if digest(env["payload"])!=env["payload_hash"]: return self._ver(env["id"],env["src"],"rejected","payload_hash_mismatch")
        body={k:env[k] for k in ["src","dst","kind","payload_hash","key_id","key_version","created"]}
        try: self.public(env["public_pem"]).verify(ub64(env["signature"]),digest(body).encode())
        except Exception: return self._ver(env["id"],env["src"],"rejected","signature_failed")
        return self._ver(env["id"],env["src"],"verified","signature_verified")
    def _ver(self,eid,src,status,reason):
        self.conn.execute("INSERT INTO verifications(envelope_id,src,status,reason) VALUES(?,?,?,?)",(eid,src,status,reason))
        self.conn.commit(); self.receipt("verification",eid,{"status":status,"reason":reason})
        return {"verified":status=="verified","envelope":eid,"reason":reason}
    def sign_credential(self,cid,claim): return self.envelope("*","credential",{"credential_id":cid,"claim":claim,"issuer":self.node})
    def sign_presentation(self,pid,disclosed): return self.envelope("*","presentation",{"presentation_id":pid,"disclosed":disclosed,"holder":self.node})
    def sign_authority(self,gid,grant): return self.envelope("*","authority",{"grant_id":gid,"grant":grant,"grantor":self.node})
    def stats(self):
        return {"node":self.node,"keys":self.conn.execute("SELECT COUNT(*) n FROM keys").fetchone()["n"],"trusted_keys":self.conn.execute("SELECT COUNT(*) n FROM trust").fetchone()["n"],"revocations":self.conn.execute("SELECT COUNT(*) n FROM revocations").fetchone()["n"],"rotations":self.conn.execute("SELECT COUNT(*) n FROM rotations").fetchone()["n"],"envelopes":self.conn.execute("SELECT COUNT(*) n FROM envelopes").fetchone()["n"],"verifications":self.conn.execute("SELECT COUNT(*) n FROM verifications").fetchone()["n"],"ledger":self.verify_ledger(),"db_integrity":self.conn.execute("PRAGMA integrity_check").fetchone()[0]}
    def bundle(self,out):
        out=Path(out)
        with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as z:
            for t in ["keys","trust","revocations","rotations","envelopes","verifications","ledger"]:
                rows=[dict(r) for r in self.conn.execute(f"SELECT * FROM {t} ORDER BY 1")]
                if t=="keys":
                    for row in rows: row["private_path"]="REDACTED"
                z.writestr(f"{t}.json",json.dumps(rows,indent=2,default=str))
            z.writestr("crypto_status.json",json.dumps(self.stats(),indent=2))
        return {"bundle":str(out),"exists":out.exists()}
def seed_demo(td):
    n=RealCryptoNode(Path(td)/"north.db","office:north",Path(td)/"keys")
    s=RealCryptoNode(Path(td)/"south.db","office:south",Path(td)/"keys")
    s.import_public_key(n.export_public_key()); n.import_public_key(s.export_public_key())
    msg=s.verify_envelope(n.envelope("office:south","heartbeat",{"status":"online"}))
    cred=n.sign_credential("credential:C-1",{"owner":"citizen:root","status":"active"}); cred_ok=s.verify_envelope(cred)
    pres=s.verify_envelope(n.sign_presentation("presentation:P-1",{"state":"MN"}))
    grant=s.verify_envelope(n.sign_authority("grant:G-1",{"scope":"wallet:read"}))
    tampered=dict(cred); tampered["payload"]={"credential_id":"credential:C-1","claim":{"status":"revoked"},"issuer":"office:north"}
    bad=s.verify_envelope(tampered)
    old=n.export_public_key(); rot=n.rotate_key(); s.import_public_key(n.export_public_key())
    post=s.verify_envelope(n.envelope("office:south","post_rotation",{"version":rot["version"]}))
    s.revoke_key(old["node"],old["key_id"],"old key retired")
    return {"message":msg,"credential":cred_ok,"presentation":pres,"authority":grant,"tampered":bad,"rotation":rot,"post_rotation":post,"north":n.stats(),"south":s.stats()}
