
from pathlib import Path
import tempfile
from shadowqueen.core import Store,Credential,CredentialLifecycle
with tempfile.TemporaryDirectory() as td:
    s=Store(Path(td)/"cred.db","queen"); lc=CredentialLifecycle(s)
    assert lc.issue(Credential.create("C-1","carbon:root","driver_license",1,"proof-1"))["status"]=="active"
    assert lc.suspend("C-1",reason="review")["to"]=="suspended"
    assert lc.renew("C-1","C-2",ttl_days=365)["ok"] is True
    assert s.get("C-1")["status"]=="replaced"
    assert s.get("C-2")["status"]=="active"
    assert lc.revoke("C-2",reason="fraud")["to"]=="revoked"
    assert lc.transition("C-2","active",reason="bad restore")["ok"] is False
    assert s.stats()["findings"]>=1
    assert s.verify_ledger()["ok"] is True
    assert s.stats()["db_integrity"]=="ok"
    assert s.bundle(Path(td)/"evidence.zip")["exists"]
print("SELFTEST PASS")
