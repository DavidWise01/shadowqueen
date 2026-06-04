
import argparse,json
from .core import FederationOps,seed_demo
def demo(a): print(json.dumps(seed_demo(FederationOps(a.db,a.federation)),indent=2))
def dashboard(a): print(json.dumps(FederationOps(a.db,a.federation).dashboard(),indent=2))
def offices(a): print(json.dumps(FederationOps(a.db,a.federation).offices(),indent=2))
def cases(a): print(json.dumps(FederationOps(a.db,a.federation).cases(),indent=2))
def stats(a): print(json.dumps(FederationOps(a.db,a.federation).stats(),indent=2))
def verify(a): print(json.dumps(FederationOps(a.db,a.federation).verify_ledger(),indent=2))
def evidence(a): print(json.dumps(FederationOps(a.db,a.federation).bundle(a.output),indent=2))
def main(argv=None):
    p=argparse.ArgumentParser(); p.add_argument("--db",default="ops.db"); p.add_argument("--federation",default="shadow-federation")
    sub=p.add_subparsers(dest="cmd",required=True)
    sub.add_parser("demo").set_defaults(func=demo); sub.add_parser("dashboard").set_defaults(func=dashboard); sub.add_parser("offices").set_defaults(func=offices); sub.add_parser("cases").set_defaults(func=cases); sub.add_parser("stats").set_defaults(func=stats); sub.add_parser("verify-ledger").set_defaults(func=verify)
    e=sub.add_parser("evidence"); e.add_argument("output"); e.set_defaults(func=evidence)
    args=p.parse_args(argv); return args.func(args)
if __name__=="__main__": raise SystemExit(main())
