
import json, tempfile
from pathlib import Path
from shadowqueen.core import Event, ShadowQueen
q = ShadowQueen()
ok = q.classify(Event.from_dict({"source_id":"ok","event_type":"five_body","features":{"inner_body":"SELF","outer_observer":"+8_CARRIER"}}))
gap = q.classify(Event.from_dict({"source_id":"gap","event_type":"five_body","features":{"gap_crossed":True}}))
ent = q.classify(Event.from_dict({"source_id":"ent","event_type":"five_body","features":{"observer_entangled":True}}))
assert ok["action"] == "allow", ok
assert gap["action"] == "quarantine", gap
assert ent["action"] == "quarantine", ent
print("SELFTEST PASS")
