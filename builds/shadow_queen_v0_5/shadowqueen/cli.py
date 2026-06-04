
import argparse, json
from pathlib import Path
from .core import Event, Store, ShadowQueen

def load_events(path):
    data = json.loads(Path(path).read_text())
    for item in (data if isinstance(data, list) else [data]):
        yield Event.from_dict(item)

def scan(args):
    store = Store(args.db)
    queen = ShadowQueen()
    for event in load_events(args.input):
        decision = queen.classify(event)
        store.record(event, decision)
        if not args.quiet:
            print(json.dumps(decision, sort_keys=True))
    if not args.quiet:
        print("STATS", json.dumps(store.stats(), sort_keys=True))

def stats(args):
    store = Store(args.db)
    payload = store.stats()
    if args.recent:
        payload["recent"] = store.recent(args.recent)
    print(json.dumps(payload, indent=2, sort_keys=True))

def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="shadowqueen.db")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("scan")
    p.add_argument("input")
    p.add_argument("--quiet", action="store_true")
    p.set_defaults(func=scan)
    p = sub.add_parser("stats")
    p.add_argument("--recent", type=int, default=0)
    p.set_defaults(func=stats)
    args = parser.parse_args(argv)
    return args.func(args)

if __name__ == "__main__":
    raise SystemExit(main())
