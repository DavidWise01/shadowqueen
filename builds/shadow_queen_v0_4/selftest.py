
from pathlib import Path
import tempfile,json
from shadowqueen.core import Store,ShadowQueen
from shadowqueen.collectors import file_snapshot,network_snapshot,process_snapshot,load_events
with tempfile.TemporaryDirectory() as td:
    td=Path(td); db=td/"sq.db"; watched=td/"watch"; watched.mkdir()
    (watched/"safe.txt").write_text("hello"); (watched/"script.sh").write_text("#!/bin/sh\necho hi\n")
    sample=td/"events.json"; sample.write_text(json.dumps([{"source_id":"shadow","event_type":"call","phase":"-1"}]))
    s=Store(db); q=ShadowQueen(s.load_memory(),s.load_risk())
    events=file_snapshot(watched,False,10)+network_snapshot(10)+process_snapshot(10)+list(load_events(sample))
    for e in events: s.record(e,q.classify(e))
    st=s.stats()
    assert st["events"]>=4
    assert "file_change" in st["by_type"]
    assert st["fingerprint_memory"]>=1
print("SELFTEST PASS")
