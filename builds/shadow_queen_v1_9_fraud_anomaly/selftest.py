
from pathlib import Path
import tempfile
from shadowqueen.core import Store,IdentityNode,TrustEdge,FraudEngine
nodes=[IdentityNode.from_dict({"entity_id":"carbon:a","entity_type":"carbon","proof_hash":"p1","trust_score":.9}),IdentityNode.from_dict({"entity_id":"silicon:q","entity_type":"silicon","proof_hash":"p2","trust_score":.9}),IdentityNode.from_dict({"entity_id":"silicon:shadow","entity_type":"silicon","proof_hash":"p3","trust_score":.05})]
edges=[TrustEdge.from_dict({"source_id":"silicon:q","target_id":"carbon:a","relation":"witness","confidence":.9}),TrustEdge.from_dict({"source_id":"silicon:q","target_id":"silicon:shadow","relation":"shadow_clone","confidence":.99}),TrustEdge.from_dict({"source_id":"carbon:a","target_id":"silicon:shadow","relation":"parent","confidence":.5})]
with tempfile.TemporaryDirectory() as td:
    s=Store(Path(td)/"fraud.db"); res=FraudEngine(s).load_graph(nodes,edges)
    assert res["subjects_scored"]>=1
    assert any(f["severity"]=="critical" for f in s.findings())
    assert s.verify_ledger()["ok"] is True
    assert s.stats()["db_integrity"]=="ok"
    assert s.bundle(Path(td)/"evidence.zip")["exists"]
print("SELFTEST PASS")
