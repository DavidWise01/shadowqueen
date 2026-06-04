
from pathlib import Path
import tempfile
from shadowqueen.core import Authority,seed_demo
with tempfile.TemporaryDirectory() as td:
    a=Authority(Path(td)/"authority.db","test-domain")
    r=seed_demo(a)
    assert r["allowed"]["allowed"] is True
    assert r["denied"]["allowed"] is False
    assert r["human_ok"]["allowed"] is True
    assert r["silicon_block"]["allowed"] is False
    assert r["after_revoke"]["allowed"] is False
    assert a.stats()["grants"]==2
    assert a.verify_ledger()["ok"] is True
    assert a.stats()["db_integrity"]=="ok"
    assert a.bundle(Path(td)/"authority.zip")["exists"]
print("SELFTEST PASS")
