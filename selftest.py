from pathlib import Path
import tempfile
from shadowqueen.core import Store, Replicator
with tempfile.TemporaryDirectory() as td:
    north=Store(Path(td)/'north.db','north'); south=Store(Path(td)/'south.db','south'); east=Store(Path(td)/'east.db','east')
    rep=Replicator(north)
    rep.issue('C-1','carbon:root','license','proof-1',['south','east'],1)
    assert north.credential('C-1')['status']=='active'
    assert len(rep.replay({'south':south,'east':east}))==2
    assert south.credential('C-1')['status']=='active'
    rep.transition('C-1','credential_suspended',['south','east'],2)
    rep.replay({'south':south,'east':east})
    assert east.credential('C-1')['status']=='suspended'
    assert north.audit_convergence([south,east],'auditor')['result']=='pass'
    stale=north.publish('credential_revoked','C-1',{'credential_id':'C-1','version':1},['south'])
    Replicator(north).deliver_to(south,stale.event_id)
    assert south.stats()['conflicts']>=1
    assert north.verify_ledger()['ok'] and south.verify_ledger()['ok']
    assert north.stats()['db_integrity']=='ok'
    assert north.bundle(Path(td)/'replication.zip')['exists']
print('SELFTEST PASS')
