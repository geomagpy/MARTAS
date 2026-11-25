#!/usr/bin/env python3
"""
NAME:
    db_truncate.py

DESCRIPTION:
    Non-blocking cleanup utility for timeseries tables in a MagPy MariaDB database.
    Unlike the 'archive' tool (which relies on DATAINFO metadata), 'db_truncate.py'
    identifies all timeseries tables matching the standard MagPy naming convention
    (xxx_xxx_xxxx_xxxx) directly from the database schema.

    Data retention is calculated dynamically based on each table's sampling rate (sr)
    and a configurable multiplier ('cleanratio'):
        retention_days = sampling_rate_in_seconds * cleanratio

    Examples (with cleanratio = 12):
        - 1 Hz data (1s)   -> keeps the last 12 days
        - 1 min data (60s) -> keeps the last 720 days (~2 years)
        - 1 hr data (3600s)-> keeps the last 43,200 days (~118 years)

    To prevent long-running InnoDB table/row locks and I/O spikes that block incoming
    sensor INSERTs, deletions are executed in small batches via 'mm.chunked_delete()',
    committing and pausing briefly between chunks, and updating 'DataMinTime' in
    DATAINFO afterward.

CONFIGURATION FILE EXAMPLE (truncate.cfg):
    # Database credential key (stored via MagPy cred)
    dbcredentials   :   cobsdb

    # Retention multiplier: deletes rows older than (sampling_rate_sec * cleanratio) days
    cleanratio      :   12

    # Batch size per DELETE transaction (optional, default: 5000)
    chunksize       :   5000

    # Substrings of table/sensor names to exclude (comma-separated)
    blacklist       :   BLV,QUAKES,Sensor2,Sensor3

    # Whitelist: if set, ONLY tables containing these substrings are processed
    #sensorlist     :   Sensor1,Sensor4

USAGE:
    # Run automatically using a configuration file
    python3 db_truncate.py -c truncate.cfg

    # Override cleanratio and restrict to specific sensors
    python3 db_truncate.py -c truncate.cfg -s Sensor1,Sensor2 -i 12

    # Dry-run (debug mode: inspects tables and sampling rates without deleting)
    python3 db_truncate.py -c truncate.cfg -D
"""

import argparse
import os
import sys
import time
from datetime import datetime, timezone
import numpy as np

from magpy.stream import DataStream
from martas.core import methods as mm


__version__ = "2.0.0"


def get_target_tables(db, sensorlist=None, blacklist=None, debug=False):
    """
    Retrieves all timeseries tables matching the 'xxx_xxx_xxxx_xxxx' pattern
    from the currently connected MariaDB database, filtered by blacklist and sensorlist.
    """
    if not db:
        return []

    sensorlist = [s.strip() for s in (sensorlist or []) if s.strip()]
    blacklist = [b.strip() for b in (blacklist or []) if b.strip()]
    blacklist.extend(["INNODB", "COLLATION"])

    if debug:
        print("   Querying information_schema.tables for current database...")

    sql = """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = DATABASE()
          AND table_type = 'BASE TABLE'
          AND table_name LIKE '%\\_%\\_%\\_%'
    """
    cursor = db.db.cursor()
    try:
        message = db._executesql(cursor, sql)
        if message:
            print(f"   SQL Error: {message}")
            return []
        fulllist = [row[0] for row in cursor.fetchall()]
    finally:
        cursor.close()

    # Keep only tables with exactly 3 underscores (xxx_xxx_xxxx_xxxx)
    schema_tables = [tab for tab in fulllist if tab.count("_") == 3]

    # Apply blacklist
    filtered_tables = [
        tab for tab in schema_tables
        if not any(bl in tab for bl in blacklist)
    ]

    # Apply optional sensor whitelist
    if sensorlist:
        filtered_tables = [
            tab for tab in filtered_tables
            if any(se in tab for se in sensorlist)
        ]

    if debug:
        print(f"   -> Tables selected for processing ({len(filtered_tables)}): {filtered_tables}")

    return filtered_tables


def parse_args():
    parser = argparse.ArgumentParser(
        description="Non-blocking truncation of old timeseries entries in a MagPy MariaDB database.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Example: python3 db_truncate.py -c truncate.cfg -s Sensor1,Sensor2 -i 12"
    )
    parser.add_argument("-c", "--config", required=True, help="Path to the configuration file")
    parser.add_argument("-i", "--ratio", type=int, help="Override cleanratio (retention multiplier)")
    parser.add_argument("-s", "--sensorlist", help="Comma-separated list of sensors to include")
    parser.add_argument("-b", "--blacklist", help="Comma-separated list of table substrings to skip")
    parser.add_argument("--chunk-size", type=int, help="Number of rows per DELETE batch (default: 5000)")
    parser.add_argument("-D", "--debug", action="store_true", help="Dry-run / debug mode (no data deleted)")
    parser.add_argument("-v", "--version", action="version", version=f"%(prog)s {__version__}")
    return parser.parse_args()


def main():
    args = parse_args()
    conf_path = os.path.abspath(args.config)

    if not os.path.isfile(conf_path):
        print(f"Error: Configuration file not found at '{conf_path}'")
        sys.exit(1)

    if args.debug:
        print(f"Running db_truncate.py v{__version__} (DEBUG / DRY-RUN MODE)")
        print("------------------------------------------------------------")

    config = mm.get_conf(conf_path)

    # Resolve parameters (CLI arguments override configuration file values)
    ratio = args.ratio if args.ratio is not None else int(config.get("cleanratio", 12))
    chunk_size = args.chunk_size if args.chunk_size is not None else int(config.get("chunksize", 5000))
    sensorlist = args.sensorlist.split(",") if args.sensorlist else config.get("sensorlist", [])
    blacklist = args.blacklist.split(",") if args.blacklist else config.get("blacklist", [])

    if args.debug:
        print(f"Parameters -> Ratio: {ratio}, Chunk size: {chunk_size}")
        print(f"Sensorlist -> {sensorlist}")
        print(f"Blacklist  -> {blacklist}")

    db = mm.connect_db(config.get("dbcredentials", "cobsdb"))
    if not db:
        print("Error: Could not connect to database.")
        sys.exit(1)

    tables = get_target_tables(db, sensorlist=sensorlist, blacklist=blacklist, debug=args.debug)

    for data in tables:
        start_time = datetime.now(timezone.utc).replace(tzinfo=None)
        print("----------------------------")
        print(f"Processing table: {data}")

        # Fetch a small sample (100 rows) to determine the sampling rate efficiently
        try:
            sample = db.get_lines(data, 100)
        except Exception as e:
            print(f"   Could not read sample lines from {data}: {e}")
            continue

        if sample.length()[0] == 0:
            print(f"   Table {data} is empty – skipping.")
            continue

        sr = sample.samplingrate()
        if np.isnan(sr) or sr <= 0:
            print(f"   Invalid sampling rate ({sr}) for {data} – skipping.")
            continue

        retention_days = sr * ratio
        print(f"   Sampling rate: {sr}s -> Retention: {retention_days:.1f} days")

        if args.debug:
            print(f"   [DEBUG] Would run chunked_delete on {data} (chunk_size={chunk_size}).")
            continue

        success = mm.chunked_delete(db, data, sr, ratio, chunk_size=chunk_size)
        elapsed_min = (datetime.now(timezone.utc).replace(tzinfo=None) - start_time).total_seconds() / 60.0

        if success:
            print(f" -> Finished {data} in {elapsed_min:.2f} minutes.")
        else:
            print(f" -> Failed cleaning {data} after {elapsed_min:.2f} minutes.")

    print("----------------------------")


if __name__ == "__main__":
    main()