from pathlib import Path
import tempfile
from shadowqueen.core import DisclosureEngine,seed_demo
with tempfile.TemporaryDirectory() as td:
    e=DisclosureEngine(Path(td)/'disclosure.db','citizen:root')
    r=seed_demo(e)
    assert r['age_state']['ok'] is True
    assert 'address' in r['age_state']['redacted']
    assert r['blocked']['ok'] is False
    assert e.verify_presentation(r['age_state']['presentation'])['ok'] is True
    assert e.stats()['presentations']==3
    assert e.verify_ledger()['ok'] is True
    assert e.stats()['db_integrity']=='ok'
    assert e.bundle(Path(td)/'disclosure.zip')['exists']
print('SELFTEST PASS')
