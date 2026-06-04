
import argparse,json
from .core import Authority,seed_demo
def demo(a): print(json.dumps(seed_demo(Authority(a.db,a.domain)),indent=2))
def grants(a): print(json.dumps(Authority(a.db,a.domain).grants(),indent=2))
def decisions(a): print(json.dumps(Authority(a.db,a.domain).decisions(),indent=2))
def stats(a): print(json.dumps(Authority(a.db,a.domain).stats(),indent=2))
def verify(a): print(json.dumps(Authority(a.db,a.domain).verify_ledger(),indent=2))
def evidence(a): print(json.dumps(Authority(a.db,a.domain).bundle(a.output),indent=2))
def main(argv=None):
    p=argparse.ArgumentParser(); p.add_argument("--db",default="authority.db"); p.add_argument("--domain",default="shadow-authority")
    sub=p.add_subparsers(dest="cmd",required=True)
    sub.add_parser("demo").set_defaults(func=demo); sub.add_parser("grants").set_defaults(func=grants); sub.add_parser("decisions").set_defaults(func=decisions); sub.add_parser("stats").set_defaults(func=stats); sub.add_parser("verify-ledger").set_defaults(func=verify)
    e=sub.add_parser("evidence"); e.add_argument("output"); e.set_defaults(func=evidence)
    args=p.parse_args(argv); return args.func(args)
if __name__=="__main__": raise SystemExit(main())
