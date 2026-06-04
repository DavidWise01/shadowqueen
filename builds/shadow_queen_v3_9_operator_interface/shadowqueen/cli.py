
import argparse,json
from .core import OperatorInterface, seed_demo
def demo(a): print(json.dumps(seed_demo(OperatorInterface(a.db,a.operator)),indent=2))
def dashboard(a): print(json.dumps(OperatorInterface(a.db,a.operator).dashboard(),indent=2))
def stats(a): print(json.dumps(OperatorInterface(a.db,a.operator).stats(),indent=2))
def verify(a): print(json.dumps(OperatorInterface(a.db,a.operator).verify_ledger(),indent=2))
def evidence(a): print(json.dumps(OperatorInterface(a.db,a.operator).bundle(a.output),indent=2))
def main(argv=None):
    p=argparse.ArgumentParser(); p.add_argument("--db",default="operator.db"); p.add_argument("--operator",default="operator:root")
    sub=p.add_subparsers(dest="cmd",required=True)
    sub.add_parser("demo").set_defaults(func=demo)
    sub.add_parser("dashboard").set_defaults(func=dashboard)
    sub.add_parser("stats").set_defaults(func=stats)
    sub.add_parser("verify-ledger").set_defaults(func=verify)
    e=sub.add_parser("evidence"); e.add_argument("output"); e.set_defaults(func=evidence)
    args=p.parse_args(argv); return args.func(args)
if __name__=="__main__": raise SystemExit(main())
