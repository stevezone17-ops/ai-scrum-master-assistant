"""
database/supabase_adapter.py
============================
Supabase PostgreSQL Database Adapter & Cursor Layer.

- Connects to Supabase PostgreSQL using the Supabase client.
- Handles INSERT, UPDATE, DELETE directly against Supabase PostgREST tables.
- Supports dictionary key access (DictRow) identical to sqlite3.Row.
- Provides fallback to SQLite when DATABASE_BACKEND=sqlite.
"""

import sqlite3
import re
import logging
from utils.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

class DictRow(dict):
    """Row wrapper permitting dict-key access (row['col']), integer access (row[0]), and dict(row)."""
    def __getitem__(self, key):
        if isinstance(key, int):
            return list(self.values())[key]
        return super().__getitem__(key)


class SupabaseCursorAdapter:
    def __init__(self, supabase_client):
        self.client = supabase_client
        self.lastrowid = None
        self.rowcount = 0
        self._results = []
        self._index = 0
        self.description = None

    def _convert_params(self, params):
        if not params:
            return ()
        if isinstance(params, (list, tuple)):
            return tuple(params)
        return (params,)

    def execute(self, sql, params=()):
        params = self._convert_params(params)
        sql_strip = sql.strip()
        sql_upper = sql_strip.upper()

        if sql_upper.startswith("INSERT"):
            return self._handle_insert(sql_strip, params)
        elif sql_upper.startswith("UPDATE"):
            return self._handle_update(sql_strip, params)
        elif sql_upper.startswith("DELETE"):
            return self._handle_delete(sql_strip, params)
        elif sql_upper.startswith("SELECT") or sql_upper.startswith("WITH") or sql_upper.startswith("PRAGMA"):
            return self._handle_select(sql_strip, params)
        else:
            logger.warning(f"[!] Unhandled SQL statement type in SupabaseCursorAdapter: {sql_strip[:50]}")
            return self

    def executemany(self, sql, params_list):
        for params in params_list:
            self.execute(sql, params)
        return self

    def _handle_insert(self, sql, params):
        # Extract table name and column names
        # Pattern: INSERT INTO table_name (col1, col2) VALUES (?, ?)
        match = re.search(r"INSERT\s+INTO\s+([^\s\(]+)\s*\(([^\)]+)\)", sql, re.IGNORECASE)
        if not match:
            raise ValueError(f"Could not parse INSERT statement: {sql}")

        table_name = match.group(1).strip("`'\" ")
        cols = [c.strip("`'\" ") for c in match.group(2).split(",")]

        if len(cols) != len(params):
            raise ValueError(f"Column count ({len(cols)}) does not match params count ({len(params)}) for table {table_name}")

        row_data = {}
        for col, val in zip(cols, params):
            row_data[col] = val

        # Execute Supabase insert
        res = self.client.table(table_name).insert(row_data).execute()
        if res.data and len(res.data) > 0:
            inserted = res.data[0]
            self.lastrowid = inserted.get('id')
            self._results = [DictRow(inserted)]
            self.rowcount = 1
        else:
            self.lastrowid = None
            self._results = []
            self.rowcount = 0
        self._index = 0
        return self

    def _handle_update(self, sql, params):
        # Extract table name, SET clause, and WHERE clause
        match = re.search(r"UPDATE\s+([^\s]+)\s+SET\s+(.*?)\s+WHERE\s+(.*)", sql, re.IGNORECASE | re.DOTALL)
        if not match:
            raise ValueError(f"Could not parse UPDATE statement: {sql}")

        table_name = match.group(1).strip("`'\" ")
        set_clause = match.group(2).strip()
        where_clause = match.group(3).strip()

        # Count placeholders in SET vs WHERE
        set_cols = [c.split("=")[0].strip("`'\" ") for c in set_clause.split(",")]
        num_set_params = len(set_cols)

        set_params = params[:num_set_params]
        where_params = params[num_set_params:]

        update_dict = {}
        for col, val in zip(set_cols, set_params):
            update_dict[col] = val

        # Build Supabase update query
        query = self.client.table(table_name).update(update_dict)

        # Parse simple WHERE conditions (e.g. id = ? or project_id = ? AND user_id = ?)
        where_conditions = re.split(r"\s+AND\s+", where_clause, flags=re.IGNORECASE)
        param_idx = 0
        for cond in where_conditions:
            cond = cond.strip()
            w_match = re.match(r"([^\s=]+)\s*(=|!=|>|<|>=|<=|IN)\s*(.+)", cond, re.IGNORECASE)
            if w_match:
                w_col = w_match.group(1).strip("`'\" ")
                op = w_match.group(2).upper()
                w_val_str = w_match.group(3).strip()

                if "?" in w_val_str:
                    w_val = where_params[param_idx]
                    param_idx += 1
                    if op == "=":
                        query = query.eq(w_col, w_val)
                    elif op == "!=":
                        query = query.neq(w_col, w_val)
                    elif op == ">":
                        query = query.gt(w_col, w_val)
                    elif op == "<":
                        query = query.lt(w_col, w_val)
                    elif op == ">=":
                        query = query.gte(w_col, w_val)
                    elif op == "<=":
                        query = query.lte(w_col, w_val)

        res = query.execute()
        self.rowcount = len(res.data) if res.data else 0
        self._results = [DictRow(r) for r in res.data] if res.data else []
        self._index = 0
        return self

    def _handle_delete(self, sql, params):
        match = re.search(r"DELETE\s+FROM\s+([^\s]+)(?:\s+WHERE\s+(.*))?", sql, re.IGNORECASE | re.DOTALL)
        if not match:
            raise ValueError(f"Could not parse DELETE statement: {sql}")

        table_name = match.group(1).strip("`'\" ")
        where_clause = match.group(2)

        query = self.client.table(table_name).delete()
        if where_clause:
            where_conditions = re.split(r"\s+AND\s+", where_clause.strip(), flags=re.IGNORECASE)
            param_idx = 0
            for cond in where_conditions:
                cond = cond.strip()
                w_match = re.match(r"([^\s=]+)\s*(=|!=|>|<|>=|<=)\s*(.+)", cond, re.IGNORECASE)
                if w_match:
                    w_col = w_match.group(1).strip("`'\" ")
                    op = w_match.group(2).upper()
                    w_val_str = w_match.group(3).strip()

                    if "?" in w_val_str:
                        w_val = params[param_idx]
                        param_idx += 1
                        if op == "=":
                            query = query.eq(w_col, w_val)
                        elif op == "!=":
                            query = query.neq(w_col, w_val)

        res = query.execute()
        self.rowcount = len(res.data) if res.data else 0
        self._results = []
        self._index = 0
        return self

    def _handle_select(self, sql, params):
        """
        Execute SELECT query by fetching live Supabase table data into an in-memory SQLite engine
        and executing the exact SQL query string against the live Supabase dataset.
        """
        tables = ['users', 'projects', 'team_members', 'sprints', 'user_stories', 'tasks', 'bugs', 'standup_updates']
        referenced_tables = [t for t in tables if re.search(r"\b" + t + r"\b", sql, re.IGNORECASE)]

        mem_conn = sqlite3.connect(":memory:")
        mem_conn.row_factory = sqlite3.Row
        mem_cursor = mem_conn.cursor()

        for table in referenced_tables:
            # Fetch live Supabase rows for table
            res = self.client.table(table).select("*").execute()
            rows = res.data or []

            if len(rows) > 0:
                cols = list(rows[0].keys())
                col_type_map = {}
                for r in rows:
                    for c, val in r.items():
                        if c not in col_type_map and val is not None:
                            if isinstance(val, bool):
                                col_type_map[c] = 'INTEGER'
                            elif isinstance(val, int):
                                col_type_map[c] = 'INTEGER'
                            elif isinstance(val, float):
                                col_type_map[c] = 'REAL'
                            else:
                                col_type_map[c] = 'TEXT'

                col_defs = ", ".join([f'"{c}" {col_type_map.get(c, "TEXT")}' for c in cols])
                mem_cursor.execute(f'CREATE TABLE "{table}" ({col_defs})')

                placeholders = ", ".join(["?"] * len(cols))
                col_names = ", ".join([f'"{c}"' for c in cols])
                insert_sql = f'INSERT INTO "{table}" ({col_names}) VALUES ({placeholders})'

                row_tuples = [tuple(r.get(c) for c in cols) for r in rows]
                mem_cursor.executemany(insert_sql, row_tuples)
            else:
                # Create empty table schema if table has 0 rows
                mem_cursor.execute(f'CREATE TABLE "{table}" (id INTEGER PRIMARY KEY)')

        # Execute query against memory DB loaded with Supabase data
        try:
            mem_cursor.execute(sql, params)
            res_rows = mem_cursor.fetchall()
            self._results = [DictRow(dict(r)) for r in res_rows]
            self.description = mem_cursor.description
        except Exception as e:
            logger.error(f"[!] Error executing SELECT in Supabase adapter: {e}\nSQL: {sql}\nParams: {params}")
            self._results = []
            self.description = None

        mem_conn.close()
        self._index = 0
        return self

    def fetchone(self):
        if self._index < len(self._results):
            row = self._results[self._index]
            self._index += 1
            return row
        return None

    def fetchall(self):
        results = self._results[self._index:]
        self._index = len(self._results)
        return results

    def close(self):
        pass


class SupabaseDatabaseAdapter:
    """Connection-like adapter exposing cursor(), execute(), commit(), and close()."""
    def __init__(self, supabase_client):
        self.client = supabase_client

    def cursor(self):
        return SupabaseCursorAdapter(self.client)

    def execute(self, sql, params=()):
        cursor = self.cursor()
        return cursor.execute(sql, params)

    def commit(self):
        pass

    def close(self):
        pass
