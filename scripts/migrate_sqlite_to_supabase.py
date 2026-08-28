"""
scripts/migrate_sqlite_to_supabase.py
======================================
One-time administrative migration script to copy data from local SQLite database
to Supabase PostgreSQL.

Usage:
    Dry-run mode (safe validation without writing to Supabase):
        python scripts/migrate_sqlite_to_supabase.py --dry-run

    Live Migration mode (upserts data into Supabase):
        python scripts/migrate_sqlite_to_supabase.py

Tables Migrated (in foreign-key dependency order):
    1. users
    2. projects
    3. team_members
    4. sprints
    5. user_stories
    6. tasks
    7. bugs
    8. standup_updates
"""

import sys
import os
import sqlite3
import argparse
import logging
from datetime import datetime

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.supabase_client import get_supabase_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("migration")

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "database", "database.db"))

MIGRATION_ORDER = [
    'users',
    'projects',
    'team_members',
    'sprints',
    'user_stories',
    'tasks',
    'bugs',
    'standup_updates'
]


def transform_record(table_name, record):
    """
    Transform SQLite record values into PostgreSQL-compatible Python types.
    """
    data = dict(record)

    # Standard transformations for NULLs / types
    for key, value in list(data.items()):
        if value is None:
            continue
        
        # Numeric conversions
        if key in ['estimated_hours', 'actual_hours']:
            try:
                data[key] = float(value)
            except (ValueError, TypeError):
                data[key] = 0.0
        elif key in ['story_points', 'created_by', 'project_id', 'user_id', 'sprint_id', 'story_id', 'assigned_to', 'reported_by']:
            try:
                data[key] = int(value)
            except (ValueError, TypeError):
                data[key] = None

    return data


def migrate_table(sqlite_conn, supabase_client, table_name, dry_run=False):
    """
    Migrate a single table from SQLite to Supabase.
    
    Returns:
        dict with keys: 'sqlite_count', 'migrated', 'skipped', 'errors'
    """
    cursor = sqlite_conn.cursor()
    cursor.execute(f"SELECT * FROM {table_name}")
    rows = cursor.fetchall()
    
    sqlite_count = len(rows)
    migrated_count = 0
    skipped_count = 0
    error_list = []

    if sqlite_count == 0:
        logger.info(f"[-] Table '{table_name}' is empty in SQLite. Skipping.")
        return {
            'sqlite_count': 0,
            'migrated': 0,
            'skipped': 0,
            'errors': []
        }

    records_to_insert = []
    for row in rows:
        try:
            transformed = transform_record(table_name, row)
            records_to_insert.append(transformed)
        except Exception as e:
            error_list.append(f"Record transformation error (ID {dict(row).get('id')}): {e}")
            skipped_count += 1

    if dry_run:
        logger.info(f"[DRY-RUN] Validated {len(records_to_insert)} records for table '{table_name}'. (No Supabase writes executed)")
        return {
            'sqlite_count': sqlite_count,
            'migrated': len(records_to_insert),
            'skipped': skipped_count,
            'errors': error_list
        }

    if not supabase_client:
        err = "Supabase client uninitialized or missing configuration."
        logger.error(f"[!] Cannot migrate '{table_name}': {err}")
        return {
            'sqlite_count': sqlite_count,
            'migrated': 0,
            'skipped': sqlite_count,
            'errors': [err]
        }

    # Execute Supabase upsert in batches of 100
    batch_size = 100
    for i in range(0, len(records_to_insert), batch_size):
        batch = records_to_insert[i:i + batch_size]
        try:
            res = supabase_client.table(table_name).upsert(batch).execute()
            migrated_count += len(batch)
        except Exception as e:
            err_msg = f"Supabase upsert failed on batch starting at index {i} for '{table_name}': {e}"
            logger.error(f"[!] {err_msg}")
            error_list.append(err_msg)
            skipped_count += len(batch)

    return {
        'sqlite_count': sqlite_count,
        'migrated': migrated_count,
        'skipped': skipped_count,
        'errors': error_list
    }


def update_postgresql_sequences(supabase_client, dry_run=False):
    """
    Query max ID per table and log sequence alignment instructions.
    """
    if dry_run or not supabase_client:
        return

    logger.info("[+] Checking maximum IDs for sequence alignment...")
    for table_name in MIGRATION_ORDER:
        try:
            res = supabase_client.table(table_name).select("id").order("id", desc=True).limit(1).execute()
            if res.data and len(res.data) > 0:
                max_id = res.data[0]['id']
                logger.info(f"   - Table '{table_name}': MAX(id) = {max_id}")
        except Exception as e:
            logger.warning(f"   - MAX(id) query skipped for '{table_name}': {e}")
    logger.info("   - Refer to fix_sequences.sql to align sequence counters in Supabase SQL Editor.")


def run_migration(dry_run=False):
    """
    Main migration controller function.
    """
    mode_str = "[DRY RUN MODE]" if dry_run else "[LIVE MIGRATION MODE]"
    logger.info("=" * 60)
    logger.info(f"  Starting SQLite -> Supabase Migration {mode_str}")
    logger.info("=" * 60)

    if not os.path.exists(DB_PATH):
        logger.error(f"[!] SQLite database not found at '{DB_PATH}'. Aborting.")
        return False

    sqlite_conn = sqlite3.connect(DB_PATH)
    sqlite_conn.row_factory = sqlite3.Row

    supabase_client = None
    if not dry_run:
        supabase_client = get_supabase_client()
        if not supabase_client:
            logger.error("[!] Supabase client initialization failed. Ensure SUPABASE_URL and SUPABASE_KEY are set in .env")
            sqlite_conn.close()
            return False

    summary = {}
    all_success = True

    for table in MIGRATION_ORDER:
        logger.info(f"\n[+] Processing table: '{table}'...")
        res = migrate_table(sqlite_conn, supabase_client, table, dry_run=dry_run)
        summary[table] = res
        if res['errors']:
            all_success = False

    if not dry_run and supabase_client:
        update_postgresql_sequences(supabase_client, dry_run=dry_run)

    sqlite_conn.close()

    # Final Migration Report
    print("\n" + "=" * 60)
    print(f"            FINAL MIGRATION REPORT {mode_str}")
    print("=" * 60)
    print(f"{'Table Name':<20} | {'SQLite Rows':<12} | {'Migrated':<10} | {'Skipped':<10} | {'Status':<10}")
    print("-" * 60)

    total_sqlite = 0
    total_migrated = 0
    total_skipped = 0

    for table in MIGRATION_ORDER:
        s = summary[table]
        total_sqlite += s['sqlite_count']
        total_migrated += s['migrated']
        total_skipped += s['skipped']
        status_label = "OK" if not s['errors'] else "WARNING"
        print(f"{table:<20} | {s['sqlite_count']:<12} | {s['migrated']:<10} | {s['skipped']:<10} | {status_label:<10}")

    print("-" * 60)
    print(f"{'TOTALS':<20} | {total_sqlite:<12} | {total_migrated:<10} | {total_skipped:<10} |")
    print("=" * 60)

    if not all_success:
        print("\n[!] Errors encountered during migration:")
        for table, s in summary.items():
            for err in s['errors']:
                print(f"  - [{table}] {err}")

    return all_success


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate SQLite database to Supabase PostgreSQL.")
    parser.add_argument("--dry-run", action="store_true", help="Perform a dry run without inserting into Supabase.")
    args = parser.parse_args()

    success = run_migration(dry_run=args.dry_run)
    sys.exit(0 if success else 1)
