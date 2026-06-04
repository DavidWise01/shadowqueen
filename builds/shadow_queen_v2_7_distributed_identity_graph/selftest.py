
from pathlib import Path
import tempfile
from shadowqueen.core import Store

with tempfile.TemporaryDirectory() as td:
    north=Store(Path(td)/"north.db","north")
    south=Store(Path(td)/"south.db","south")
    east=Store(Path(td)/"east.db","east")
    north.add_node("person","carbon:root",{"name":"Root User","dob":"1981-06-21","domain":"carbon"},["south","east"])
    north.replay({"south":south,"east":east})
    assert len(south.nodes())==1
    pid=north.nodes()[0]["id"]
    north.add_edge(pid,"credential","C-1","holds",{"credential_type":"license"},["south","east"])
    north.add_edge(pid,"address","A-1","resides_at",{"state":"MN"},["south","east"])
    north.replay({"south":south,"east":east})
    assert len(east.edges())==2
    assert north.audit([south,east])["result"]=="pass"
    north.add_node("person","carbon:root-copy",{"name":"Root User","dob":"1981-06-21","domain":"carbon"},[])
    assert north.duplicate_scan()
    assert north.verify_ledger()["ok"] and south.verify_ledger()["ok"]
    assert north.stats()["db_integrity"]=="ok"
    assert north.bundle(Path(td)/"identity_graph.zip")["exists"]
print("SELFTEST PASS")
