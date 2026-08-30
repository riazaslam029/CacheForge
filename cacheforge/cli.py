"""
CacheForge Command-Line Interface.
Built strictly using standard library argparse for zero third-party dependencies.
"""

import argparse
import json
import sys
from typing import List, Dict, Any, Optional

from cacheforge.database import CacheForgeDB
from cacheforge.benchmark import BenchmarkRunner
from cacheforge.errors import CacheForgeError, KeyNotFoundError


def parse_fields(field_args: Optional[List[str]]) -> Dict[str, Any]:
    """Parse list of 'name=value' strings into dictionary."""
    if not field_args:
        return {}
    fields = {}
    for arg in field_args:
        if "=" in arg:
            k, v = arg.split("=", 1)
            fields[k.strip()] = v.strip()
        else:
            fields[arg.strip()] = True
    return fields


def main(argv: Optional[List[str]] = None) -> int:
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    parent_parser.add_argument("--debug", action="store_true", help="Print full exception traceback on error")

    parser = argparse.ArgumentParser(
        prog="cacheforge",
        description="CacheForge — Zero-dependency embedded storage engine with WAL, search, TTL, and crash recovery.",
        parents=[parent_parser]
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # init
    p_init = subparsers.add_parser("init", parents=[parent_parser], help="Initialize a new CacheForge database directory")
    p_init.add_argument("database", help="Path to database directory")

    # set
    p_set = subparsers.add_parser("set", parents=[parent_parser], help="Set a key-value record")
    p_set.add_argument("database", help="Path to database directory")
    p_set.add_argument("key", help="Record key")
    p_set.add_argument("value", help="Record value string")
    p_set.add_argument("--ttl", type=float, help="TTL expiration time in seconds")
    p_set.add_argument("--field", action="append", help="Secondary metadata field (format: key=value)")

    # get
    p_get = subparsers.add_parser("get", parents=[parent_parser], help="Get a key value")
    p_get.add_argument("database", help="Path to database directory")
    p_get.add_argument("key", help="Record key")

    # delete
    p_del = subparsers.add_parser("delete", parents=[parent_parser], help="Delete a key")
    p_del.add_argument("database", help="Path to database directory")
    p_del.add_argument("key", help="Record key")

    # exists
    p_exists = subparsers.add_parser("exists", parents=[parent_parser], help="Check if key exists")
    p_exists.add_argument("database", help="Path to database directory")
    p_exists.add_argument("key", help="Record key")

    # ttl
    p_ttl = subparsers.add_parser("ttl", parents=[parent_parser], help="Get remaining TTL in seconds")
    p_ttl.add_argument("database", help="Path to database directory")
    p_ttl.add_argument("key", help="Record key")

    # expire
    p_expire = subparsers.add_parser("expire", parents=[parent_parser], help="Set key expiration in seconds")
    p_expire.add_argument("database", help="Path to database directory")
    p_expire.add_argument("key", help="Record key")
    p_expire.add_argument("seconds", type=float, help="TTL in seconds")

    # persist
    p_persist = subparsers.add_parser("persist", parents=[parent_parser], help="Remove key expiration")
    p_persist.add_argument("database", help="Path to database directory")
    p_persist.add_argument("key", help="Record key")

    # search
    p_search = subparsers.add_parser("search", parents=[parent_parser], help="Full-text inverted search over values")
    p_search.add_argument("database", help="Path to database directory")
    p_search.add_argument("query", help="Text search query string")

    # query
    p_query = subparsers.add_parser("query", parents=[parent_parser], help="Query records by secondary fields")
    p_query.add_argument("database", help="Path to database directory")
    p_query.add_argument("--field", action="append", required=True, help="Secondary field match (format: name=value)")

    # cleanup
    p_cleanup = subparsers.add_parser("cleanup", parents=[parent_parser], help="Eagerly purge expired keys")
    p_cleanup.add_argument("database", help="Path to database directory")

    # stats
    p_stats = subparsers.add_parser("stats", parents=[parent_parser], help="Display database statistics")
    p_stats.add_argument("database", help="Path to database directory")

    # verify
    p_verify = subparsers.add_parser("verify", parents=[parent_parser], help="Verify database SHA-256 data integrity")
    p_verify.add_argument("database", help="Path to database directory")

    # recover
    p_recover = subparsers.add_parser("recover", parents=[parent_parser], help="Recover database from WAL/crash")
    p_recover.add_argument("database", help="Path to database directory")

    # compact
    p_compact = subparsers.add_parser("compact", parents=[parent_parser], help="Compact database log and reclaim space")
    p_compact.add_argument("database", help="Path to database directory")

    # snapshot
    p_snap = subparsers.add_parser("snapshot", parents=[parent_parser], help="Create point-in-time database snapshot")
    p_snap.add_argument("database", help="Path to database directory")
    p_snap.add_argument("--name", help="Custom snapshot directory name")

    # export
    p_export = subparsers.add_parser("export", parents=[parent_parser], help="Export active records to JSON file")
    p_export.add_argument("database", help="Path to database directory")
    p_export.add_argument("filepath", help="Output JSON file path")

    # import
    p_import = subparsers.add_parser("import", parents=[parent_parser], help="Import records from JSON file")
    p_import.add_argument("database", help="Path to database directory")
    p_import.add_argument("filepath", help="Input JSON file path")

    # benchmark
    p_bench = subparsers.add_parser("benchmark", parents=[parent_parser], help="Run reproducible CacheForge benchmarks")
    p_bench.add_argument("--records", type=int, default=5000, help="Number of records for benchmark")

    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    use_json = args.json
    debug = args.debug

    try:
        if args.command == "init":
            with CacheForgeDB(args.database) as db:
                msg = f"Initialized CacheForge database at '{args.database}'"
                if use_json:
                    print(json.dumps({"status": "OK", "message": msg, "database": args.database}))
                else:
                    print(f"✓ {msg}")
            return 0

        elif args.command == "set":
            fields = parse_fields(args.field)
            with CacheForgeDB(args.database) as db:
                db.set(args.key, args.value, ttl=args.ttl, fields=fields)
                if use_json:
                    print(json.dumps({
                        "status": "OK", "key": args.key, "value": args.value,
                        "ttl": args.ttl, "fields": fields
                    }))
                else:
                    print(f"OK (set '{args.key}')")
            return 0

        elif args.command == "get":
            with CacheForgeDB(args.database) as db:
                rec = db.get(args.key)
                if rec is None:
                    if use_json:
                        print(json.dumps({"error": f"Key not found: '{args.key}'"}, indent=2))
                    else:
                        sys.stderr.write(f"Error: Key not found: '{args.key}'\n")
                    return 3
                if use_json:
                    res = {
                        "key": rec.key,
                        "value": rec.value_str,
                        "sequence": rec.sequence,
                        "timestamp_us": rec.timestamp_us,
                        "expire_us": rec.expire_us,
                        "fields": rec.fields
                    }
                    print(json.dumps(res, indent=2))
                else:
                    print(rec.value_str)
            return 0

        elif args.command == "delete":
            with CacheForgeDB(args.database) as db:
                success = db.delete(args.key)
                if not success:
                    if use_json:
                        print(json.dumps({"error": f"Key not found: '{args.key}'"}))
                    else:
                        sys.stderr.write(f"Error: Key not found: '{args.key}'\n")
                    return 3
                if use_json:
                    print(json.dumps({"status": "OK", "deleted_key": args.key}))
                else:
                    print(f"OK (deleted '{args.key}')")
            return 0

        elif args.command == "exists":
            with CacheForgeDB(args.database) as db:
                found = db.exists(args.key)
                if use_json:
                    print(json.dumps({"key": args.key, "exists": found}))
                else:
                    print("true" if found else "false")
            return 0 if found else 1

        elif args.command == "ttl":
            with CacheForgeDB(args.database) as db:
                rem_ttl = db.ttl(args.key)
                if use_json:
                    print(json.dumps({"key": args.key, "ttl_seconds": rem_ttl}))
                else:
                    if rem_ttl < 0:
                        print(f"Key '{args.key}' has no expiration (infinite)")
                    else:
                        print(f"{rem_ttl:.2f} seconds remaining")
            return 0

        elif args.command == "expire":
            with CacheForgeDB(args.database) as db:
                db.expire(args.key, args.seconds)
                if use_json:
                    print(json.dumps({"status": "OK", "key": args.key, "ttl_seconds": args.seconds}))
                else:
                    print(f"OK (set TTL={args.seconds}s on '{args.key}')")
            return 0

        elif args.command == "persist":
            with CacheForgeDB(args.database) as db:
                db.persist(args.key)
                if use_json:
                    print(json.dumps({"status": "OK", "key": args.key, "persistent": True}))
                else:
                    print(f"OK (removed TTL on '{args.key}')")
            return 0

        elif args.command == "search":
            with CacheForgeDB(args.database) as db:
                results = db.search(args.query)
                if use_json:
                    json_res = [
                        {"key": rec.key, "value": rec.value_str, "score": round(score, 4)}
                        for rec, score in results
                    ]
                    print(json.dumps(json_res, indent=2))
                else:
                    if not results:
                        print("No matching records found.")
                    else:
                        print(f"Found {len(results)} matching record(s):")
                        for rec, score in results:
                            print(f"  [{score:.4f}] {rec.key} -> {rec.value_str[:80]}")
            return 0

        elif args.command == "query":
            field_conds = parse_fields(args.field)
            with CacheForgeDB(args.database) as db:
                records = db.query(field_conds)
                if use_json:
                    json_res = [
                        {"key": r.key, "value": r.value_str, "fields": r.fields}
                        for r in records
                    ]
                    print(json.dumps(json_res, indent=2))
                else:
                    if not records:
                        print("No records matched query criteria.")
                    else:
                        print(f"Query matched {len(records)} record(s):")
                        for r in records:
                            print(f"  {r.key} -> {r.value_str} (fields: {r.fields})")
            return 0

        elif args.command == "cleanup":
            with CacheForgeDB(args.database) as db:
                purged = db.cleanup()
                if use_json:
                    print(json.dumps({"status": "OK", "purged_keys": purged}))
                else:
                    print(f"Purged {purged} expired key(s).")
            return 0

        elif args.command == "stats":
            with CacheForgeDB(args.database) as db:
                st = db.stats()
                if use_json:
                    print(json.dumps(st, indent=2))
                else:
                    print("CacheForge Database Statistics")
                    print("==============================")
                    print(f"Directory:           {st['database_dir']}")
                    print(f"Sequence Number:     {st['sequence_number']}")
                    print(f"Total Records:       {st['total_records']}")
                    print(f"Live Records:        {st['live_records']}")
                    print(f"Expired Records:     {st['expired_records']}")
                    print(f"Data Size:           {st['data_size_bytes'] / 1024:.2f} KB")
                    print(f"Journal Size:        {st['journal_size_bytes'] / 1024:.2f} KB")
                    print(f"Indexed Fields:      {st['indexed_fields_count']}")
                    print(f"Search Terms:        {st['search_terms_count']}")
                    print(f"Integrity Status:    {st['integrity_status']}")
                    print(f"Recovery Status:     {st['recovery_status']}")
            return 0

        elif args.command == "verify":
            with CacheForgeDB(args.database) as db:
                rep = db.verify()
                if use_json:
                    print(json.dumps(rep.to_dict(), indent=2))
                else:
                    print(rep.format_text())
            return 0 if rep.is_valid else 5

        elif args.command == "recover":
            with CacheForgeDB(args.database, auto_recover=False) as db:
                rep = db.recover()
                if use_json:
                    print(json.dumps(rep.to_dict(), indent=2))
                else:
                    print(rep.format_text())
            return 0

        elif args.command == "compact":
            with CacheForgeDB(args.database) as db:
                rep = db.compact()
                if use_json:
                    print(json.dumps(rep.to_dict(), indent=2))
                else:
                    print(rep.format_text())
            return 0

        elif args.command == "snapshot":
            with CacheForgeDB(args.database) as db:
                snap_path = db.snapshot(args.name)
                if use_json:
                    print(json.dumps({"status": "OK", "snapshot_path": snap_path}))
                else:
                    print(f"Created snapshot at '{snap_path}'")
            return 0

        elif args.command == "export":
            with CacheForgeDB(args.database) as db:
                db.export_data(args.filepath)
                if use_json:
                    print(json.dumps({"status": "OK", "export_path": args.filepath}))
                else:
                    print(f"Exported data to '{args.filepath}'")
            return 0

        elif args.command == "import":
            with CacheForgeDB(args.database) as db:
                count = db.import_data(args.filepath)
                if use_json:
                    print(json.dumps({"status": "OK", "imported_records": count}))
                else:
                    print(f"Imported {count} record(s) from '{args.filepath}'")
            return 0

        elif args.command == "benchmark":
            bench_res = BenchmarkRunner.run_benchmark(num_records=args.records)
            if use_json:
                print(json.dumps(bench_res.to_dict(), indent=2))
            else:
                print(bench_res.format_text())
            return 0

        return 0

    except CacheForgeError as cfe:
        if debug:
            raise cfe
        sys.stderr.write(f"Error ({cfe.__class__.__name__}): {cfe.message}\n")
        return cfe.exit_code
    except Exception as e:
        if debug:
            raise e
        sys.stderr.write(f"Unexpected Error: {e}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
