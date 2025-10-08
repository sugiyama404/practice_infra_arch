#!/usr/bin/env python3
"""Lightweight diagnostic for pg_uuid: show table metadata and capture insert exceptions concisely.

Run from the project venv: .venv/bin/python diag_pg_uuid.py
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError


def load_env(env_path=".env"):
    if os.path.exists(env_path):
        with open(env_path) as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())


def concise_print(label, value):
    print(f"{label}:", value)


def inspect_table(engine, table):
    with engine.connect() as conn:
        # to_regclass
        try:
            t_exists = conn.execute(
                text("SELECT to_regclass(:t)"), {"t": table}
            ).scalar()
        except Exception as e:
            t_exists = f"error: {e}"
        concise_print(f"to_regclass({table})", t_exists)

        # columns
        try:
            cols = conn.execute(
                text(
                    "SELECT column_name, data_type, column_default, is_identity, is_nullable \
                     FROM information_schema.columns WHERE table_name = :t ORDER BY ordinal_position"
                ),
                {"t": table},
            ).fetchall()
            concise_print(f"columns({table}) count", len(cols))
            for c in cols:
                # print only name and type and default presence
                concise_print(
                    "  col",
                    {
                        "name": c[0],
                        "type": c[1],
                        "default": c[2] is not None,
                        "is_identity": c[3],
                    },
                )
        except Exception as e:
            concise_print(f"columns({table}) error", str(e))

        # pg_get_serial_sequence
        try:
            seq = conn.execute(
                text("SELECT pg_get_serial_sequence(:t, 'id')"), {"t": table}
            ).scalar()
        except Exception as e:
            seq = f"error: {e}"
        concise_print(f"pg_get_serial_sequence({table})", seq)

        # try a very small transactional insert and capture only the exception text
        try:
            with conn.begin() as tr:
                if table == "seq_id_test":
                    conn.execute(
                        text(
                            "INSERT INTO seq_id_test (payload) VALUES (jsonb_build_object('test',1))"
                        )
                    )
                elif table == "snowflake_test":
                    conn.execute(
                        text(
                            "INSERT INTO snowflake_test (id, payload) VALUES (cast(1234567890 as bigint), jsonb_build_object('test',1))"
                        )
                    )
                else:
                    conn.execute(
                        text(
                            f"INSERT INTO {table} (id, payload) VALUES (:id, jsonb_build_object('test',1))"
                        ),
                        {"id": "00000000-0000-0000-0000-000000000000"},
                    )
            concise_print(f"insert_test({table})", "OK (rolled back)")
        except SQLAlchemyError as sae:
            # SQLAlchemy wraps DBAPI errors; show concise message
            concise_print(
                f"insert_test({table}) FAILED",
                str(sae.__dict__.get("orig") or str(sae)),
            )
        except Exception as e:
            concise_print(f"insert_test({table}) FAILED", str(e))


def main():
    load_env()
    dsn = os.getenv("PG_UUID_DSN")
    if not dsn:
        print("PG_UUID_DSN not set in environment or .env")
        sys.exit(2)

    engine = create_engine(dsn)
    print("Using DSN:", dsn)

    for table in ["seq_id_test", "snowflake_test"]:
        print("\n===", table, "===")
        inspect_table(engine, table)


if __name__ == "__main__":
    main()
