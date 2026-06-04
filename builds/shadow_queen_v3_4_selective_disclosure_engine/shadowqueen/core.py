import json, hashlib, sqlite3, time, zipfile
from pathlib import Path

def digest(o): return hashlib.sha256(json.dumps(o,sort_keys=True,default=str).encode()).hexdigest()

class DisclosureEngine:
    def __init__(self,path='disclosure.db',owner='citizen:local'):
        self.owner=owner; self.conn=sqlite3.connect(Path(path)); self.conn.row_factory=sqlite3.Row
        self.conn.executescript('''
        CREATE TABLE IF NOT EXISTS credentials(id TEXT PRIMARY KEY,type TEXT,issuer TEXT,status TEXT,claim TEXT,claim_hash TEXT,trust REAL);
        CREATE TABLE IF NOT EXISTS policies(id TEXT PRIMARY KEY,name TEXT,allowed TEXT,required TEXT,min_trust REAL,policy_hash TEXT);
        CREATE TABLE IF NOT EXISTS presentations(id TEXT PRIMARY KEY,ts REAL,audience TEXT,credential TEXT,policy TEXT,status TEXT,disclosed TEXT,redacted TEXT,proof_hash TEXT,details TEXT);
        CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,ts REAL,type TEXT,subject TEXT,details TEXT);
        CREATE TABLE IF NOT EXISTS ledger(seq INTEGER PRIMARY KEY AUTOINCREMENT,kind TEXT,subject TEXT,payload_hash TEXT,prev_hash TEXT,entry_hash TEXT);
        '''); self.conn.commit()
    def last_hash(self):
        r=self.conn.execute('SELECT entry_hash FROM ledger ORDER BY seq DESC LIMIT 1').fetchone()
        return r['entry_hash'] if r else 'GENESIS'
    def receipt(self,k,s,p):
        prev=self.last_hash(); ph=digest(p); eh=digest({'kind':k,'subject':s,'payload_hash':ph,'prev_hash':prev})
        self.conn.execute('INSERT INTO ledger(kind,subject,payload_hash,prev_hash,entry_hash) VALUES(?,?,?,?,?)',(k,s,ph,prev,eh)); self.conn.commit()
    def event(self,t,s,d=None):
        self.conn.execute('INSERT INTO events(ts,type,subject,details) VALUES(?,?,?,?)',(time.time(),t,s,json.dumps(d or {},default=str)))
        self.receipt('event',s,{'type':t,'details':d or {}})
    def verify_ledger(self):
        prev='GENESIS'; n=0
        for r in self.conn.execute('SELECT seq,kind,subject,payload_hash,prev_hash,entry_hash FROM ledger ORDER BY seq'):
            exp=digest({'kind':r['kind'],'subject':r['subject'],'payload_hash':r['payload_hash'],'prev_hash':prev})
            if r['prev_hash']!=prev: return {'ok':False,'seq':r['seq'],'reason':'prev_hash_mismatch'}
            if r['entry_hash']!=exp: return {'ok':False,'seq':r['seq'],'reason':'entry_hash_mismatch'}
            prev=r['entry_hash']; n+=1
        return {'ok':True,'entries':n,'head':prev}
    def import_credential(self,cid,typ,issuer,claim,status='active',trust=80):
        ch=digest(claim); self.conn.execute('INSERT OR REPLACE INTO credentials VALUES(?,?,?,?,?,?,?)',(cid,typ,issuer,status,json.dumps(claim),ch,float(trust)))
        self.event('credential_imported',cid,{'type':typ,'issuer':issuer,'claim_hash':ch}); self.conn.commit(); return {'credential':cid,'claim_hash':ch}
    def create_policy(self,name,allowed,required=None,min_trust=60):
        ph=digest({'name':name,'allowed':allowed,'required':required or [],'min_trust':min_trust}); pid='policy:'+ph[:16]
        self.conn.execute('INSERT OR REPLACE INTO policies VALUES(?,?,?,?,?,?)',(pid,name,json.dumps(allowed),json.dumps(required or []),float(min_trust),ph))
        self.event('policy_created',pid,{'name':name,'policy_hash':ph}); self.conn.commit(); return {'policy':pid,'hash':ph}
    def getc(self,cid):
        r=self.conn.execute('SELECT * FROM credentials WHERE id=?',(cid,)).fetchone(); return dict(r) if r else None
    def getp(self,pid):
        r=self.conn.execute('SELECT * FROM policies WHERE id=?',(pid,)).fetchone(); return dict(r) if r else None
    def disclose(self,cid,pid,audience):
        c=self.getc(cid); p=self.getp(pid)
        if not c: return {'ok':False,'reason':'missing_credential'}
        if not p: return {'ok':False,'reason':'missing_policy'}
        claim=json.loads(c['claim']); allowed=json.loads(p['allowed']); required=json.loads(p['required']); errors=[]
        if c['status']!='active': errors.append('credential_not_active')
        if float(c['trust'])<float(p['min_trust']): errors.append('trust_below_minimum')
        for f in required:
            if f not in claim or claim.get(f) in (None,''): errors.append('missing_required:'+f)
            if f not in allowed: errors.append('required_not_allowed:'+f)
        disclosed={k:claim[k] for k in allowed if k in claim}; redacted=sorted([k for k in claim if k not in disclosed])
        proof={'owner':self.owner,'credential':cid,'policy':pid,'audience':audience,'disclosed':disclosed,'redacted':redacted,'claim_hash':c['claim_hash'],'policy_hash':p['policy_hash'],'errors':errors}
        h=digest(proof); pres='presentation:'+h[:16]; status='ready' if not errors else 'blocked'
        self.conn.execute('INSERT OR REPLACE INTO presentations VALUES(?,?,?,?,?,?,?,?,?,?)',(pres,time.time(),audience,cid,pid,status,json.dumps(disclosed),json.dumps(redacted),h,json.dumps(proof,default=str)))
        self.event('presentation_created',pres,{'status':status,'audience':audience,'proof_hash':h}); self.conn.commit()
        return {'ok':not errors,'presentation':pres,'status':status,'disclosed':disclosed,'redacted':redacted,'proof_hash':h,'errors':errors}
    def verify_presentation(self,pres):
        r=self.conn.execute('SELECT * FROM presentations WHERE id=?',(pres,)).fetchone()
        if not r: return {'ok':False,'reason':'missing_presentation'}
        return {'ok':digest(json.loads(r['details']))==r['proof_hash'],'presentation':pres,'status':r['status']}
    def presentations(self): return [dict(r) for r in self.conn.execute('SELECT id,audience,credential,policy,status,disclosed,redacted,proof_hash FROM presentations ORDER BY ts')]
    def stats(self):
        return {'owner':self.owner,'credentials':self.conn.execute('SELECT COUNT(*) n FROM credentials').fetchone()['n'],'policies':self.conn.execute('SELECT COUNT(*) n FROM policies').fetchone()['n'],'presentations':self.conn.execute('SELECT COUNT(*) n FROM presentations').fetchone()['n'],'events':self.conn.execute('SELECT COUNT(*) n FROM events').fetchone()['n'],'ledger':self.verify_ledger(),'db_integrity':self.conn.execute('PRAGMA integrity_check').fetchone()[0]}
    def bundle(self,out):
        out=Path(out)
        with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
            for t in ['credentials','policies','presentations','events','ledger']:
                z.writestr(f'{t}.json',json.dumps([dict(r) for r in self.conn.execute(f'SELECT * FROM {t} ORDER BY 1')],indent=2,default=str))
            z.writestr('manifest.json',json.dumps({'stats':self.stats(),'created':time.time()},indent=2))
        return {'bundle':str(out),'exists':out.exists()}

def seed_demo(e):
    e.import_credential('credential:license:C-1','driver_license','north',{'full_name':'Root User','dob':'1981-06-21','state':'MN','class':'D','address':'private road','license_number':'SECRET-123','trust_score':88},trust=88)
    p1=e.create_policy('age_state_check',['dob','state'],['dob','state'],60)
    p2=e.create_policy('full_license_check',['full_name','dob','state','class'],['full_name','dob','state','class'],60)
    p3=e.create_policy('blocked_high_trust',['state'],['state'],95)
    return {'age_state':e.disclose('credential:license:C-1',p1['policy'],'retailer'),'full':e.disclose('credential:license:C-1',p2['policy'],'law_enforcement'),'blocked':e.disclose('credential:license:C-1',p3['policy'],'high_trust_gate')}
