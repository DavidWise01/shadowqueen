import argparse,json
from .core import DisclosureEngine,seed_demo
def demo(a): print(json.dumps(seed_demo(DisclosureEngine(a.db,a.owner)),indent=2))
def presentations(a): print(json.dumps(DisclosureEngine(a.db,a.owner).presentations(),indent=2))
def stats(a): print(json.dumps(DisclosureEngine(a.db,a.owner).stats(),indent=2))
def verify(a): print(json.dumps(DisclosureEngine(a.db,a.owner).verify_ledger(),indent=2))
def evidence(a): print(json.dumps(DisclosureEngine(a.db,a.owner).bundle(a.output),indent=2))
def main(argv=None):
    p=argparse.ArgumentParser(); p.add_argument('--db',default='disclosure.db'); p.add_argument('--owner',default='citizen:local')
    sub=p.add_subparsers(dest='cmd',required=True)
    sub.add_parser('demo').set_defaults(func=demo); sub.add_parser('presentations').set_defaults(func=presentations); sub.add_parser('stats').set_defaults(func=stats); sub.add_parser('verify-ledger').set_defaults(func=verify)
    e=sub.add_parser('evidence'); e.add_argument('output'); e.set_defaults(func=evidence)
    a=p.parse_args(argv); return a.func(a)
if __name__=='__main__': raise SystemExit(main())
