"""Write the Markdown report for a baseline results file.

    python scripts/make_report.py outputs/baseline-facesynthetics-seed0/results.json

The report is printed, or saved with --out. Use it to rebuild a report after the
report format changes, without running the measurements again.
"""

import argparse
import json
import sys
from pathlib import Path

from mantelet import report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("results", type=Path, help="A results.json file from run_baseline.py")
    parser.add_argument("--out", type=Path, default=None, help="Save the report here")
    parser.add_argument("--force", action="store_true", help="Overwrite an existing --out file")
    args = parser.parse_args(argv)

    if args.out is not None and args.out.exists() and not args.force:
        return fail(f"'{args.out}' already exists. Use --force to overwrite it")
    try:
        results = json.loads(args.results.read_text(encoding="utf-8"))
        text = report.render_report(results)
    except (OSError, ValueError, KeyError, TypeError) as error:
        return fail(f"could not build a report from '{args.results}': {error!r}")
    if args.out is None:
        print(text, end="")
    else:
        args.out.write_text(text, encoding="utf-8")
        print(f"Saved the report to {args.out}")
    return 0


def fail(message):
    print(f"Error: {message}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
