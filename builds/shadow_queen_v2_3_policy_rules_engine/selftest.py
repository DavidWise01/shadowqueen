
from pathlib import Path
import tempfile
from shadowqueen.core import Store,Credential,CredentialLifecycle,Actor
with tempfile.TemporaryDirectory() as td:
    s=Store(Path(td)/"policy.db"); lc=CredentialLifecycle(s)
    clerk=Actor("c1","clerk",.8); reg=Actor("r1","registrar",.9); aud=Actor("a1","auditor",.9)
    assert lc.issue(Credential.create("D1","carbon:root","license",365,"p"),clerk)["ok"] is False
    assert lc.issue(Credential.create("C1","carbon:root","license",30,"p"),reg)["ok"] is True
    assert lc.suspend("C1",clerk)["ok"] is True
    assert lc.revoke("C1",clerk)["ok"] is False
    assert lc.revoke("C1",aud,finding=True)["ok"] is True
    assert lc.issue(Credential.create("C2","carbon:root","license",365,"p2"),reg)["ok"] is True
    assert lc.renew("C2","C3",reg)["ok"] is False
    assert s.stats()["policy_decisions"]>=6
    assert s.verify_ledger()["ok"] is True
    assert s.stats()["db_integrity"]=="ok"
    assert s.bundle(Path(td)/"policy.zip")["exists"]
print("SELFTEST PASS")
