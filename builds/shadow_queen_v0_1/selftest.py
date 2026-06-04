
from shadowqueen.engine import Event, ShadowQueen
q=ShadowQueen()
for name,e,exp in [('clean',Event('a','call',phase='+1'),'allow'),('shadow',Event('s','call',phase='-1'),'quarantine'),('peek',Event('p','session',layer='L5',features={'payload_read_attempt':True}),'quarantine'),('bad_wiggle',Event('w','io',wiggle_sequence='++++'),'quarantine')]:
    got=q.classify(e)['action']; assert got==exp,(name,got,exp)
q.classify(Event('parent','call',phase='-1'))
child=q.classify(Event('child','call',phase='0',parent_id='parent'))
assert child['action']=='track',child
print('SELFTEST PASS')
