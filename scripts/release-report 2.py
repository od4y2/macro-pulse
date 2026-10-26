r"""Release-gate report runner (unit S20).

Runs the catalog-wide release sweep (``macropulse.ops.release``) against a
target database and prints - optionally writes - the deterministic report.
Held series are honest outcomes printed with their named gate reasons; the
process exits 0 whenever the sweep completes, because a held series is a
finding, not a runner failure.

Against production (the go-live database), pass the Neon URL via
``--db-url`` - never via a shell-visible value; read it from the local
gitignored env file:

    NEON="$(grep '^NEON_DATABASE_URL=' .env.local | cut -d= -f2- | tr -d '"')"
    PYTHONPATH=src .venv/bin/python scripts/release-report.py \\
        --db-url "${NEON/#postgresql:\/\//postgresql+psycopg://}" \\
        --output evidence/S20/release-gates.txt

Bootstrap note: the evidence file this writes is itself cited by portfolio
documentation; on a fresh clone the first run materializes it.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from macropulse.db.base import make_engine, make_session_factory
from macropulse.ops.release import DEFAULT_RELEASE_WINDOW, release_sweep

REPO_ROOT = Path(__file__).resolve().parents[1]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scripts/release-report.py",
        description=(
            "Release sweep: evaluate the S09 publication gate for every "
            "planned catalog series and materialize robust_z for published "
            "ones (idempotent re-runs)."
        ),
    )
    parser.add_argument(
        "--db-url",
        default=None,
        help="database URL (default: DATABASE_URL env / local docker-compose)",
    )
    parser.add_argument(
        "--window",
        type=int,
        default=DEFAULT_RELEASE_WINDOW,
        help=f"standardization window in frequency steps (default {DEFAULT_RELEASE_WINDOW})",
    )
    parser.add_argument(
        "--no-derive",
        action="store_true",
        help="evaluate gates only; write no derived rows",
    )
    parser.add_argument(
        "--indicator",
        action="append",
        default=None,
        metavar="ID",
        help="restrict to one indicator_id (repeatable)",
    )
    parser.add_argument(
        "--country",
        action="append",
        default=None,
        metavar="ISO3",
        help="restrict to one panel country (repeatable)",
    )
    parser.add_argument(
        "--output",
        default=None,
        metavar="PATH",
        help="also write the report to this file",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    engine = make_engine(args.db_url)
    factory = make_session_factory(engine)
    try:
        with factory() as session:
            report = release_sweep(
                session,
                window=args.window,
                derive=not args.no_derive,
                indicator_ids=args.indicator,
                country_iso3s=args.country,
            )
    finally:
        engine.dispose()

    text = report.to_text()
    print(text)
    if args.output is not None:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n", encoding="utf-8")
        print(f"\nwrote: {path}")
    summary = report.summary()
    print(
        f"\nrelease sweep complete: {summary['published']}/{summary['series_total']}"
        f" published, {summary['held']} held"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
