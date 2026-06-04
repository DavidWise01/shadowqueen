
from pathlib import Path
import tempfile
from shadowqueen.real_crypto import RealCryptoNode,seed_demo
with tempfile.TemporaryDirectory() as td:
    r=seed_demo(td)
    assert r["message"]["verified"]
    assert r["credential"]["verified"]
    assert r["presentation"]["verified"]
    assert r["authority"]["verified"]
    assert not r["tampered"]["verified"]
    assert r["post_rotation"]["verified"]
    n=RealCryptoNode(Path(td)/"north.db","office:north",Path(td)/"keys")
    s=RealCryptoNode(Path(td)/"south.db","office:south",Path(td)/"keys")
    assert n.stats()["keys"]==2
    assert s.stats()["revocations"]==1
    assert n.stats()["ledger"]["ok"]
    assert s.stats()["ledger"]["ok"]
    assert n.bundle(Path(td)/"real_crypto.zip")["exists"]
print("SELFTEST PASS")
