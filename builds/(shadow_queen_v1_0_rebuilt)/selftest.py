
from shadowqueen.core import Event, ShadowQueen

q = ShadowQueen()
e = Event(source_id="test", event_type="unit")
r = q.classify(e)

assert r["action"] == "allow"

bad = Event(
    source_id="bad",
    event_type="session",
    layer="L5",
    features={"payload_read_attempt": True}
)

r2 = q.classify(bad)
assert r2["action"] == "quarantine"

print("SELFTEST PASS")
