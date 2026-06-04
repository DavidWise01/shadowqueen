
from pathlib import Path
import tempfile
from shadowqueen.core import TrustStore, seed_demo
with tempfile.TemporaryDirectory() as td:
    s=TrustStore(Path(td)/'trust.db','north')
    seed_demo(s)
    computed=s.compute_all()
    assert len(computed)==4
    scores={r['subject_id']:r for r in s.scores()}
    assert scores['person:root']['severity']=='trusted', scores['person:root']
    assert scores['person:synthetic']['severity']=='quarantine', scores['person:synthetic']
    audit=s.audit('auditor')
    assert audit['result']=='critical'
    assert s.verify_ledger()['ok'] is True
    assert s.stats()['db_integrity']=='ok'
    assert s.bundle(Path(td)/'trust.zip')['exists']
print('SELFTEST PASS')
