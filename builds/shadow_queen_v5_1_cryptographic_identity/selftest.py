
from pathlib import Path
import tempfile
from shadowqueen.crypto_identity import CryptoIdentity,seed_demo
with tempfile.TemporaryDirectory() as td:
    r=seed_demo(td)
    assert r["message"]["verified"] is True
    assert r["credential"]["verified"] is True
    assert r["presentation"]["verified"] is True
    assert r["authority"]["verified"] is True
    assert r["tampered"]["verified"] is False
    assert r["post_rotation"]["verified"] is True
    n=CryptoIdentity(Path(td)/"north.db","office:north","MN")
    s=CryptoIdentity(Path(td)/"south.db","office:south","IA")
    assert n.stats()["keys"]==2
    assert s.stats()["rejected"]==1
    assert n.stats()["ledger"]["ok"] is True
    assert s.stats()["ledger"]["ok"] is True
    assert n.bundle(Path(td)/"crypto.zip")["exists"]
print("SELFTEST PASS")
