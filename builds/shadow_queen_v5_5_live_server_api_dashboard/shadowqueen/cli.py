import argparse
from .server import run
p=argparse.ArgumentParser();p.add_argument('--host',default='127.0.0.1');p.add_argument('--port',type=int,default=8787);p.add_argument('--data',default='data/live_state.json');p.add_argument('--web',default='web');a=p.parse_args();run(a.host,a.port,a.data,a.web)
