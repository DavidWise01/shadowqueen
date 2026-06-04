
import argparse,json,tempfile
from .reporting import Reporting,seed_demo
def demo(a):
    with tempfile.TemporaryDirectory() as td: print(json.dumps(seed_demo(td),indent=2))
def status(a): print(json.dumps(Reporting(a.db,a.node,a.reports).stats(),indent=2))
def packet(a): print(json.dumps(Reporting(a.db,a.node,a.reports).make_packet(a.subject),indent=2))
def evidence(a): print(json.dumps(Reporting(a.db,a.node,a.reports).bundle(a.output),indent=2))
def main(argv=None):
    p=argparse.ArgumentParser(); p.add_argument("--db",default="reports.db"); p.add_argument("--node",default="office:north"); p.add_argument("--reports",default="reports")
    sub=p.add_subparsers(dest="cmd",required=True)
    sub.add_parser("demo").set_defaults(func=demo); sub.add_parser("status").set_defaults(func=status)
    pk=sub.add_parser("packet"); pk.add_argument("--subject",default="release"); pk.set_defaults(func=packet)
    ev=sub.add_parser("evidence"); ev.add_argument("output"); ev.set_defaults(func=evidence)
    args=p.parse_args(argv); return args.func(args)
if __name__=="__main__": raise SystemExit(main())
