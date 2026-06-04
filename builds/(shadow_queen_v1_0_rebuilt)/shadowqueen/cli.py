
import argparse
from .daemon import run_daemon

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["daemon"])
    parser.add_argument("--config")
    args = parser.parse_args()

    if args.command == "daemon":
        print(run_daemon(args.config))

if __name__ == "__main__":
    main()
