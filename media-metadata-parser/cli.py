"""Command-line entry point: scan/index a directory, search the index,
inspect a single file's raw extraction without touching the database.

    python cli.py index <db_path> <root_dir>
    python cli.py search <db_path> <query>
    python cli.py filter <db_path> [--category X] [--creator Y] [--format Z]
    python cli.py stats <db_path>
    python cli.py inspect <file_path>
    python cli.py clear <db_path> [--yes]
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import logging
import sys

from metaindex import indexer, schema, search
from metaparser import extractor


def _cmd_index(args: argparse.Namespace) -> None:
    stats_result = indexer.index_directory(args.db_path, args.root_dir)
    print(
        f"scanned={stats_result.scanned} indexed={stats_result.indexed} "
        f"unchanged={stats_result.skipped_unchanged} failed={stats_result.failed}"
    )


def _cmd_search(args: argparse.Namespace) -> None:
    results = search.full_text_search(args.db_path, args.query, limit=args.limit)
    _print_results(results)


def _cmd_filter(args: argparse.Namespace) -> None:
    results = search.filter_search(
        args.db_path,
        category=args.category,
        creator_id=args.creator,
        file_format=args.format,
        min_duration=args.min_duration,
        max_duration=args.max_duration,
        limit=args.limit,
    )
    _print_results(results)


def _cmd_stats(args: argparse.Namespace) -> None:
    print(json.dumps(search.stats(args.db_path), indent=2))


def _cmd_inspect(args: argparse.Namespace) -> None:
    meta = extractor.extract(args.file_path)
    print(json.dumps(dataclasses.asdict(meta), indent=2, default=str))


def _cmd_clear(args: argparse.Namespace) -> None:
    if not args.yes:
        confirm = input(f"This deletes every indexed row in {args.db_path} (schema/indexes are kept). Continue? [y/N] ")
        if confirm.strip().lower() not in ("y", "yes"):
            print("aborted")
            return
    conn = schema.open_db(args.db_path)
    try:
        schema.clear(conn)
    finally:
        conn.close()
    print(f"cleared index at {args.db_path}")


def _print_results(results: list[search.SearchResult]) -> None:
    if not results:
        print("no matches")
        return
    for r in results:
        bits = [r.filename]
        if r.category:
            bits.append(f"[{r.category}/{r.subcategory}]" if r.subcategory else f"[{r.category}]")
        if r.duration_secs:
            bits.append(f"{r.duration_secs:.1f}s")
        if r.creator_id:
            bits.append(f"by {r.creator_id}")
        if r.has_errors:
            bits.append("(partial extraction)")
        print(" ".join(bits))
        print(f"    {r.path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Media metadata parser / indexer / search CLI")
    parser.add_argument("-v", "--verbose", action="store_true", help="enable debug logging")
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_index = subparsers.add_parser("index", help="scan a directory and (re)build the index")
    p_index.add_argument("db_path")
    p_index.add_argument("root_dir")
    p_index.set_defaults(func=_cmd_index)

    p_search = subparsers.add_parser("search", help="free-text search over the index")
    p_search.add_argument("db_path")
    p_search.add_argument("query")
    p_search.add_argument("--limit", type=int, default=50)
    p_search.set_defaults(func=_cmd_search)

    p_filter = subparsers.add_parser("filter", help="structured filter search over the index")
    p_filter.add_argument("db_path")
    p_filter.add_argument("--category")
    p_filter.add_argument("--creator")
    p_filter.add_argument("--format")
    p_filter.add_argument("--min-duration", type=float, dest="min_duration")
    p_filter.add_argument("--max-duration", type=float, dest="max_duration")
    p_filter.add_argument("--limit", type=int, default=50)
    p_filter.set_defaults(func=_cmd_filter)

    p_stats = subparsers.add_parser("stats", help="summary counts for the index")
    p_stats.add_argument("db_path")
    p_stats.set_defaults(func=_cmd_stats)

    p_inspect = subparsers.add_parser("inspect", help="run extraction on one file, print raw metadata, no DB involved")
    p_inspect.add_argument("file_path")
    p_inspect.set_defaults(func=_cmd_inspect)

    p_clear = subparsers.add_parser(
        "clear", help="delete all indexed rows and reclaim disk space (schema/indexes are kept, safe to re-index afterward)"
    )
    p_clear.add_argument("db_path")
    p_clear.add_argument("-y", "--yes", action="store_true", help="skip the confirmation prompt")
    p_clear.set_defaults(func=_cmd_clear)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
