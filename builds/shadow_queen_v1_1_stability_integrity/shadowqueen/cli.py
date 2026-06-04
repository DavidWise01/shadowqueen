
import argparse, json
from pathlib import Path
from .core import Event, Store, ShadowQueen
from .daemon import run_daemon, load_config

def load_events(path):
    data = json.loads(Path(path).read_text())
    for item in (data if isinstance(data, list) else [data]):
        yield Event.from_dict(item)

def scan(args):
    store = Store(args.db)
    queen = ShadowQueen(store)
    for event in load_events(args.input):
        decision = queen.classify(event)
        store.record_event(event, decision)
        if not args.quiet:
            print(json.dumps(decision, sort_keys=True))
    if not args.quiet:
        print("STATS", json.dumps(store.stats(), sort_keys=True))

def daemon(args):
    print(json.dumps(run_daemon(args.config), indent=2, sort_keys=True))

def init_config(args):
    cfg = load_config(args.output)
    print(json.dumps({"wrote": args.output, "config": cfg}, indent=2, sort_keys=True))

def stats(args):
    print(json.dumps(Store(args.db).stats(), indent=2, sort_keys=True))

def main(argv=None):
    parser = argparse.ArgumentParser(prog="shadowqueen")
    parser.add_argument("--db", default="shadowqueen.db")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("scan")
    p.add_argument("input")
    p.add_argument("--quiet", action="store_true")
    p.set_defaults(func=scan)

    p = sub.add_parser("daemon")
    p.add_argument("--config")
    p.set_defaults(func=daemon)

    p = sub.add_parser("init-config")
    p.add_argument("output")
    p.set_defaults(func=init_config)

    p = sub.add_parser("stats")
    p.set_defaults(func=stats)

    args = parser.parse_args(argv)
    return args.func(args)

if __name__ == "__main__":
    raise SystemExit(main())
