import argparse
import json

from pyramid import build


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", default="chunks")
    args = parser.parse_args()
    if args.sample == "chunks":
        chunks = [[3, -2, 5], [1, -7, 4, 2]]
    elif args.sample == "peaks":
        chunks = [[-10, -3], [8, 12]]
    else:
        raise SystemExit("unknown sample")
    print(json.dumps(build(chunks), separators=(",", ":")))


if __name__ == "__main__":
    main()
