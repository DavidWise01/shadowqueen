
from shadowqueen.core import Event, ShadowQueen
q=ShadowQueen()
ok=q.classify(Event.from_dict({"source_id":"ok","event_type":"nested_closure","features":{"null_count":2,"outer_wrap":True}}))
single=q.classify(Event.from_dict({"source_id":"single","event_type":"nested_closure","features":{"null_count":1}}))
exposed=q.classify(Event.from_dict({"source_id":"exposed","event_type":"nested_closure","features":{"internals_exposed":True}}))
assert ok["action"]=="allow"
assert single["action"]=="quarantine"
assert exposed["action"]=="quarantine"
print("SELFTEST PASS")
