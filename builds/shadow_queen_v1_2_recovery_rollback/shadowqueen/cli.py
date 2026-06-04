
import argparse, json
from pathlib import Path
from .core import Event, Store, ShadowQueen, RecoveryManager
from .daemon import run_daemon, load_config

def load_events(path):
    data = json.loads(Path(path).read_text())
    for item in (data if isinstance(data, list) else [data]):
        yield Event.from_dict(item)

def scan(args):
    store = Store(args.db)
    queen = ShadowQueen()
    recovery = RecoveryManager(store, args.recovery_dir)

    if args.checkpoint:
        recovery.checkpoint(args.checkpoint, args.config)

    for event in load_events(args.input):
        decision = queen.classify(event)
        store.record_event(event, decision)
        if decision["action"] == "quarantine" and args.checkpoint_on_quarantine:
            recovery.checkpoint("quarantine", args.config)
        if not args.quiet:
            print(json.dumps(decision, sort_keys=True))

    if not args.quiet:
        print("STATS", json.dumps(store.stats(), sort_keys=True))

def checkpoint(args):
    store = Store(args.db)
    recovery = RecoveryManager(store, args.recovery_dir)
    print(json.dumps(recovery.checkpoint(args.label, args.config), indent=2, sort_keys=True))

def restore(args):
    store = Store(args.db)
    recovery = RecoveryManager(store, args.recovery_dir)
    print(json.dumps(recovery.restore(args.label, args.restore_config_to), indent=2, sort_keys=True))

def evidence(args):
    store = Store(args.db)
    recovery = RecoveryManager(store, args.recovery_dir)
    print(json.dumps(recovery.evidence_bundle(args.output, args.label), indent=2, sort_keys=True))

def daemon(args):
    print(json.dumps(run_daemon(args.config), indent=2, sort_keys=True))

def stats(args):
    print(json.dumps(Store(args.db).stats(), indent=2, sort_keys=True))

def main(argv=None):
    p = argparse.ArgumentParser(prog="shadowqueen")
    p.add_argument("--db", default="shadowqueen.db")
    p.add_argument("--recovery-dir", default="recovery")
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("scan")
    a.add_argument("input")
    a.add_argument("--quiet", action="store_true")
    a.add_argument("--checkpoint")
    a.add_argument("--config")
    a.add_argument("--checkpoint-on-quarantine", action="store_true")
    a.set_defaults(func=scan)

    a = sub.add_parser("checkpoint")
    a.add_argument("label")
    a.add_argument("--config")
    a.set_defaults(func=checkpoint)

    a = sub.add_parser("restore")
    a.add_argument("--label")
    a.add_argument("--restore-config-to")
    a.set_defaults(func=restore)

    a = sub.add_parser("evidence")
    a.add_argument("output")
    a.add_argument("--label")
    a.set_defaults(func=evidence)

    a = sub.add_parser("daemon")
    a.add_argument("--config")
    a.set_defaults(func=daemon)

    sub.add_parser("stats").set_defaults(func=stats)

    args = p.parse_args(argv)
    return args.func(args)

if __name__ == "__main__":
    raise SystemExit(main())
