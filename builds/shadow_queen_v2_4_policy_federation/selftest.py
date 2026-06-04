
from pathlib import Path
import tempfile,json
from shadowqueen.core import Store
remote={"office_id":"south","version":2,"rules":[
{"rule_id":"issue.registrar","action":"issue","role":"registrar","allow":True,"conditions":{"min_trust":0.5},"reason":"south registrar may issue","priority":100,"version":2},
{"rule_id":"renew.registrar","action":"renew","role":"registrar","allow":True,"conditions":{"status":["active","suspended"],"window_days":180},"reason":"south renewal window","priority":100,"version":2},
{"rule_id":"revoke.clerk.deny","action":"revoke","role":"clerk","allow":True,"conditions":{"status":["suspended"]},"reason":"south permits clerk revoke","priority":100,"version":2}]}
with tempfile.TemporaryDirectory() as td:
    s=Store(Path(td)/"fed.db","north")
    assert s.export_bundle()["office_id"]=="north"
    res=s.import_bundle(remote)
    assert res["conflict_count"]>=2, res
    assert any(c["kind"]=="allow_deny_mismatch" for c in s.conflicts())
    assert s.audit("auditor-x")["result"]=="warning"
    s.override("renew.registrar","south","accept_remote","queen","accept window")
    assert s.verify_ledger()["ok"] is True
    assert s.stats()["db_integrity"]=="ok"
    assert s.bundle_zip(Path(td)/"evidence.zip")["exists"]
print("SELFTEST PASS")
