
from pathlib import Path
import tempfile
from shadowqueen.core import Store,PeerNode,P2PRuntime,P2PMessage
with tempfile.TemporaryDirectory() as td:
    queen=Store(Path(td)/"queen.db","queen")
    north=Store(Path(td)/"north.db","north")
    qr=P2PRuntime(queen); nr=P2PRuntime(north)
    qr.add_peer(PeerNode("north","office",.9))
    nr.add_peer(PeerNode("queen","queen",.95))
    msg=qr.send("north","identity_update",{"person_id":"P-1","fingerprint":"abc"})
    res=qr.deliver_to(north,msg.msg_id)
    assert res["delivered"] is True
    assert north.stats()["inbox"]==1
    bad=P2PMessage(msg.msg_id,"queen","north","identity_update",{"person_id":"P-1","fingerprint":"tampered"},msg.ts,msg.signature)
    r=north.receive(bad)
    assert r["verified"] is False
    assert north.stats()["conflicts"]==1
    assert queen.verify_ledger()["ok"] is True
    assert north.verify_ledger()["ok"] is True
    assert queen.bundle(Path(td)/"queen.zip")["exists"]
print("SELFTEST PASS")
