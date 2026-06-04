
from pathlib import Path
import tempfile,time
from shadowqueen.core import Store,PeerNode,P2PRuntime,P2PMessage
with tempfile.TemporaryDirectory() as td:
    queen=Store(Path(td)/"queen.db","queen"); north=Store(Path(td)/"north.db","north")
    qr=P2PRuntime(queen); nr=P2PRuntime(north)
    qr.add_peer(PeerNode("north","office",.9)); nr.add_peer(PeerNode("queen","queen",.95))
    msg=qr.send("north","identity_update",{"person_id":"P-1","fingerprint":"abc"})
    assert qr.deliver_to(north,msg.msg_id)["delivered"] is True
    assert "replay_nonce" in north.receive(msg)["reasons"]
    bad=P2PMessage(msg.msg_id,"queen","north","identity_update",{"x":"tampered"},msg.ts,msg.nonce,msg.ttl_seconds,msg.signature)
    assert "bad_signature" in north.receive(bad)["reasons"]
    exp=P2PMessage.create("queen","north","late",{"x":1},ttl=1)
    exp=P2PMessage(exp.msg_id,exp.from_node,exp.to_node,exp.kind,exp.payload,time.time()-10,exp.nonce,1,exp.signature)
    assert "message_expired" in north.receive(exp)["reasons"]
    assert north.stats()["conflicts"]>=3
    assert queen.verify_ledger()["ok"] and north.verify_ledger()["ok"]
    assert queen.bundle(Path(td)/"queen.zip")["exists"]
print("SELFTEST PASS")
