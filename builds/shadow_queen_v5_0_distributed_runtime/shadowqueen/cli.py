
import argparse,json,tempfile
from .runtime import Node,demo
def run_demo(a):
    with tempfile.TemporaryDirectory() as td: print(json.dumps(demo(td),indent=2))
def status(a): print(json.dumps(Node(a.db,a.node,a.region).status(),indent=2))
def evidence(a): print(json.dumps(Node(a.db,a.node,a.region).bundle(a.output),indent=2))
def main(argv=None):
    p=argparse.ArgumentParser(); p.add_argument("--db",default="runtime.db"); p.add_argument("--node",default="office:north"); p.add_argument("--region",default="local")
    sub=p.add_subparsers(dest="cmd",required=True)
    sub.add_parser("demo").set_defaults(func=run_demo); sub.add_parser("status").set_defaults(func=status)
    e=sub.add_parser("evidence"); e.add_argument("output"); e.set_defaults(func=evidence)
    args=p.parse_args(argv); return args.func(args)
if __name__=="__main__": raise SystemExit(main())
