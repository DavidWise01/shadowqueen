
from pathlib import Path
import tempfile,json
from shadowqueen.core import Event,ShadowQueen,Store
from shadowqueen.collector import follow_existing_jsonl

q=ShadowQueen()
assert q.classify(Event("a","call",phase="+1"))["action"]=="allow"
assert q.classify(Event("s","call",phase="-1"))["action"]=="quarantine"
assert q.classify(Event("p","session",layer="L5",features={"payload_read_attempt":True}))["action"]=="quarantine"

with tempfile.TemporaryDirectory() as td:
    td=Path(td); db=td/"sq.db"; stream=td/"events.jsonl"
    stream.write_text(
        json.dumps({"source_id":"live-clean","event_type":"call","phase":"+1"})+"\n"+
        json.dumps({"source_id":"live-shadow","event_type":"call","phase":"-1"})+"\n"+
        json.dumps({"source_id":"live-peek","event_type":"session","layer":"L5","features":{"payload_read_attempt":True}})+"\n"
    )
    s=Store(db); q=ShadowQueen(s.load_memory(),s.load_risk())
    for e in follow_existing_jsonl(stream):
        d=q.classify(e); s.record(e,d)
    st=s.stats()
    assert st["events"]==3
    assert st["by_action"]["allow"]==1
    assert st["by_action"]["quarantine"]==2
print("SELFTEST PASS")
