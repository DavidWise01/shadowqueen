
import argparse,json,time
from pathlib import Path
from .engine import Event,ShadowQueen
def load_events(path):
    text=Path(path).read_text(encoding='utf-8')
    data=json.loads(text)
    for item in (data if isinstance(data,list) else [data]): yield Event.from_dict(item)
def main(argv=None):
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest='cmd',required=True)
    s=sub.add_parser('scan'); s.add_argument('input'); sub.add_parser('demo'); args=p.parse_args(argv); q=ShadowQueen()
    if args.cmd=='demo':
        events=[Event('clean-1','agent_call',time.time(),phase='+1'),Event('shadow-1','agent_call',time.time(),phase='-1',parent_id='clean-1'),Event('peek-1','session',time.time(),layer='L5',features={'payload_read_attempt':True}),Event('bad-wiggle','io',time.time(),wiggle_sequence='++++'),Event('mem-1','memory',time.time(),features={'memory_import':True,'shadow_read_pass':False}),Event('child-shadow','agent_call',time.time(),parent_id='shadow-1',phase='0')]
    else: events=list(load_events(args.input))
    for e in events: print(json.dumps({'event':e.source_id,**q.classify(e)},sort_keys=True))
    return 0
if __name__=='__main__': raise SystemExit(main())
