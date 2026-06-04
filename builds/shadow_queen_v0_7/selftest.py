
from pathlib import Path
import tempfile
from shadowqueen.core import Event, Store, ShadowQueen
with tempfile.TemporaryDirectory() as td:
    s=Store(Path(td)/"sq.db"); q=ShadowQueen()
    events=[
      Event.from_dict({"source_id":"ok","event_type":"nested_closure","features":{"null_count":2}}),
      Event.from_dict({"source_id":"bad","event_type":"nested_closure","features":{"null_count":1}}),
      Event.from_dict({"source_id":"peek","event_type":"five_body","layer":"L5","features":{"payload_read_attempt":True}})
    ]
    for e in events:
        d=q.classify(e); a=q.alerts.alert_for(e,d); s.record(e,d,a)
    st=s.stats()
    assert st["events"]==3
    assert st["alerts"]==2
    assert "critical" in st["by_severity"]
    out=Path(td)/"report.json"; s.export_report(out)
    assert out.exists()
print("SELFTEST PASS")
