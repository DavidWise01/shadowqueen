
from pathlib import Path
import tempfile
from shadowqueen.core import Store,IdentityProof,TrustEdge,TrustGraph

nodes=[
    IdentityProof.from_dict({"entity_id":"carbon:a","entity_type":"carbon","identity_hash":"c1","trust_score":.8}),
    IdentityProof.from_dict({"entity_id":"silicon:q","entity_type":"silicon","identity_hash":"s1","trust_score":.9}),
    IdentityProof.from_dict({"entity_id":"silicon:clone","entity_type":"silicon","identity_hash":"s2","trust_score":.1})
]
edges=[
    TrustEdge.from_dict({"source_id":"silicon:q","target_id":"carbon:a","relation":"witness","confidence":.9}),
    TrustEdge.from_dict({"source_id":"silicon:q","target_id":"silicon:clone","relation":"shadow_clone","confidence":.99}),
    TrustEdge.from_dict({"source_id":"carbon:a","target_id":"silicon:clone","relation":"parent","confidence":.5})
]
with tempfile.TemporaryDirectory() as td:
    s=Store(Path(td)/"tg.db"); g=TrustGraph(s)
    result=g.ingest(nodes,edges)
    assert result["nodes"]==3
    assert result["clone_edges"]==1
    assert result["domain_crossings"]==1
    assert s.verify_ledger()["ok"] is True
    assert s.stats()["db_integrity"]=="ok"
    bundle=s.bundle(Path(td)/"evidence.zip")
    assert Path(bundle["bundle"]).exists()
print("SELFTEST PASS")
