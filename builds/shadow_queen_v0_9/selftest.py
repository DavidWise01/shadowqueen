
from pathlib import Path
import tempfile
from shadowqueen.core import Event,Store,ShadowQueen,PolicyEngine
with tempfile.TemporaryDirectory() as td:
    td=Path(td); s=Store(td/"sq.db"); q=ShadowQueen(s); p=PolicyEngine(s,td/"quarantine")
    for _ in range(3):
        e=Event.from_dict({"source_id":"a","event_type":"process_snapshot"})
        d=q.classify(e,learn_mode=True); s.record_event(e,d,learn=True); p.apply(e,d,"audit")
    bad=Event.from_dict({"source_id":"peek","event_type":"session","layer":"L5","features":{"payload_read_attempt":True}})
    d=q.classify(bad); s.record_event(bad,d); pol=p.apply(bad,d,"apply")
    assert d["severity"]=="critical"
    assert pol["policy"]=="denylist_and_quarantine_copy"
    again=q.classify(bad)
    assert again["reason"]=="denylisted_source"
    st=s.stats()
    assert st["denylist"]==1
    assert st["policy_actions"]>=4
print("SELFTEST PASS")
