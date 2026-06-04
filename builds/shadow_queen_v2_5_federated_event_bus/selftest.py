
from pathlib import Path
import tempfile
from shadowqueen.core import Store,EventBus,FederatedEvent
with tempfile.TemporaryDirectory() as td:
    north=Store(Path(td)/"north.db","north")
    south=Store(Path(td)/"south.db","south")
    east=Store(Path(td)/"east.db","east")
    bus=EventBus(north)
    ev=bus.publish("credential_issued","C-1",{"subject":"carbon:root","credential_type":"license"},targets=["south","east"])
    assert ev.verify()
    res=bus.replay({"south":south,"east":east})
    assert len(res)==2 and all(x["delivered"] for x in res)
    assert south.receive(ev,"north")["status"]=="duplicate"
    assert north.audit_convergence([south,east],"auditor")["result"]=="pass"
    bad=FederatedEvent(ev.event_id,ev.origin_office,ev.event_type,ev.subject,{"tampered":1},ev.causal_chain,ev.ts,ev.event_hash)
    assert east.receive(bad,"north")["accepted"] is False
    assert north.verify_ledger()["ok"] and south.verify_ledger()["ok"] and east.verify_ledger()["ok"]
    assert north.stats()["db_integrity"]=="ok"
    assert north.bundle(Path(td)/"bus.zip")["exists"]
print("SELFTEST PASS")
