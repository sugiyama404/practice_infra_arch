"""Utility helpers for the cross-database ID lookup benchmarking suite."""

from __future__ import annotations

import json
import os
import random
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
import redis
import sqlalchemy as sa
from dotenv import load_dotenv
from mysql.connector import MySQLConnection, connect as mysql_connect
from mysql.connector.cursor import MySQLCursor
from psycopg2.extras import Json, execute_batch
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.dialects import postgresql
from tqdm.auto import tqdm

# ---------------------------------------------------------------------------
# Configuration helpers
# ---------------------------------------------------------------------------

DEFAULT_SEED = int(os.getenv("SEED", 42))
DEFAULT_BATCH_SIZE = int(os.getenv("BATCH_SIZE", 20_000))
DEFAULT_LOOKUPS = int(os.getenv("LOOKUP_ITERATIONS", 10_000))


@dataclass
class BenchmarkConfig:
    """Runtime knobs controlling the benchmark behaviour."""

    batch_size: int = DEFAULT_BATCH_SIZE
    lookup_iterations: int = DEFAULT_LOOKUPS
    seed: int = DEFAULT_SEED


@dataclass
class DatasetInfo:
    """Metadata about a dataset used in the benchmark."""

    database: str
    id_type: str
    table: str
    id_column: str
    samples: Sequence[Any]


@dataclass
class ResultRow:
    database: str
    id_type: str
    operation: str
    avg_ms: float
    p95_ms: float
    min_ms: float
    max_ms: float
    lookups: int


# ---------------------------------------------------------------------------
# Snowflake ID generation
# ---------------------------------------------------------------------------


class SnowflakeGenerator:
    """Simple Snowflake (Twitter style) ID generator."""

    def __init__(
        self,
        node_id: int = 1,
        node_bits: int = 10,
        sequence_bits: int = 12,
        epoch_ms: int = 1_609_459_200_000,  # 2020-01-01
    ) -> None:
        self.node_bits = node_bits
        self.sequence_bits = sequence_bits
        self.node_id = node_id & ((1 << node_bits) - 1)
        self.epoch_ms = epoch_ms
        self.sequence_mask = (1 << sequence_bits) - 1
        self.last_timestamp = -1
        self.sequence = 0

    def _timestamp(self) -> int:
        return int(time.time() * 1000)

    def _wait_next_millis(self, current: int) -> int:
        while True:
            now = self._timestamp()
            if now > current:
                return now

    def generate(self) -> int:
        now = self._timestamp()
        if now < self.last_timestamp:
            # clock rolled back, wait for the next tick
            now = self._wait_next_millis(self.last_timestamp)
        if now == self.last_timestamp:
            self.sequence = (self.sequence + 1) & self.sequence_mask
            if self.sequence == 0:
                now = self._wait_next_millis(now)
        else:
            self.sequence = 0
        self.last_timestamp = now
        timestamp_part = (now - self.epoch_ms) << (self.node_bits + self.sequence_bits)
        node_part = self.node_id << self.sequence_bits
        return timestamp_part | node_part | self.sequence


snowflake = SnowflakeGenerator()


def uuid7() -> uuid.UUID:
    """Generate a UUIDv7 using stdlib if available, otherwise fallback."""

    if hasattr(uuid, "uuid7"):
        return uuid.uuid7()

    # Manual implementation based on draft RFC 4122bis
    unix_ts_ms = int(time.time() * 1000)
    rand_a = random.getrandbits(12)
    rand_b = random.getrandbits(62)
    time_mid = unix_ts_ms & 0xFFFF
    time_low = (unix_ts_ms >> 32) & 0xFFFFFFFF
    version = 0x7000 | (rand_a & 0x0FFF)
    variant = 0x8000 | ((rand_b >> 48) & 0x3FFF)
    node = rand_b & 0xFFFFFFFFFFFF
    return uuid.UUID(
        fields=(time_low, time_mid, version, variant >> 8, variant & 0xFF, node)
    )


# ---------------------------------------------------------------------------
# Connection helpers
# ---------------------------------------------------------------------------


def load_environment(dotenv_path: str = ".env") -> None:
    """Load environment variables from a .env file if present."""

    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path)


def create_engine(dsn: str, echo: bool = False) -> Engine:
    return sa.create_engine(dsn, echo=echo, pool_pre_ping=True)


@contextmanager
def postgres_connection(dsn: str):
    engine = create_engine(dsn)
    with engine.connect() as conn:
        yield conn


def mysql_connection(dsn: str) -> MySQLConnection:
    return mysql_connect(dsn)


@dataclass
class ConnectionBundle:
    pg_mixed: Engine
    pg_uuid: Engine
    mysql: Engine
    redis: redis.Redis


def build_connections() -> ConnectionBundle:
    load_environment()
    pg_mixed_dsn = os.getenv("PG_MIXED_DSN")
    pg_uuid_dsn = os.getenv("PG_UUID_DSN")
    mysql_dsn = os.getenv("MYSQL_DSN")
    redis_url = os.getenv("REDIS_URL")

    if not all([pg_mixed_dsn, pg_uuid_dsn, mysql_dsn, redis_url]):
        raise RuntimeError(
            "Missing DSN(s). Please configure .env or environment variables."
        )

    redis_client = redis.from_url(redis_url, decode_responses=False)
    return ConnectionBundle(
        pg_mixed=create_engine(pg_mixed_dsn),
        pg_uuid=create_engine(pg_uuid_dsn),
        mysql=create_engine(mysql_dsn),
        redis=redis_client,
    )


# ---------------------------------------------------------------------------
# Schema & data preparation
# ---------------------------------------------------------------------------

POSTGRES_TABLES = {
    "seq_id_test": """
        CREATE TABLE IF NOT EXISTS seq_id_test (
            id BIGSERIAL PRIMARY KEY,
            payload JSONB NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_seq_id_test_id ON seq_id_test (id);
    """,
    "uuid_v4_test": """
        CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
        CREATE EXTENSION IF NOT EXISTS pgcrypto;
        CREATE TABLE IF NOT EXISTS uuid_v4_test (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            payload JSONB NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_uuid_v4_test_id ON uuid_v4_test (id);
    """,
    "uuid_v7_test": """
        CREATE TABLE IF NOT EXISTS uuid_v7_test (
            id UUID PRIMARY KEY,
            payload JSONB NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_uuid_v7_test_id ON uuid_v7_test (id);
    """,
    "snowflake_test": """
        CREATE TABLE IF NOT EXISTS snowflake_test (
            id BIGINT PRIMARY KEY,
            payload JSONB NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_snowflake_test_id ON snowflake_test (id);
    """,
}

MYSQL_TABLES = {
    "seq_id_test": """
        CREATE TABLE IF NOT EXISTS seq_id_test (
            id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
            payload JSON NOT NULL,
            INDEX idx_seq_id_test_id (id)
        ) ENGINE=InnoDB;
    """,
    "uuid_v4_test": """
        CREATE TABLE IF NOT EXISTS uuid_v4_test (
            id CHAR(36) NOT NULL PRIMARY KEY,
            payload JSON NOT NULL,
            INDEX idx_uuid_v4_test_id (id)
        ) ENGINE=InnoDB;
    """,
    "uuid_v7_test": """
        CREATE TABLE IF NOT EXISTS uuid_v7_test (
            id CHAR(36) NOT NULL PRIMARY KEY,
            payload JSON NOT NULL,
            INDEX idx_uuid_v7_test_id (id)
        ) ENGINE=InnoDB;
    """,
    "snowflake_test": """
        CREATE TABLE IF NOT EXISTS snowflake_test (
            id BIGINT NOT NULL PRIMARY KEY,
            payload JSON NOT NULL,
            INDEX idx_snowflake_test_id (id)
        ) ENGINE=InnoDB;
    """,
}


def bootstrap_postgres(engine: Engine) -> None:
    with engine.begin() as conn:
        for ddl in POSTGRES_TABLES.values():
            conn.execute(text(ddl))


def bootstrap_mysql(engine: Engine) -> None:
    with engine.begin() as conn:
        for ddl in MYSQL_TABLES.values():
            conn.execute(text(ddl))


PayloadGenerator = Callable[[int], Dict[str, Any]]


def random_payload_factory(seed: int) -> PayloadGenerator:
    rng = random.Random(seed)

    def _payload(_: int) -> Dict[str, Any]:
        return {
            "score": rng.random(),
            "flag": rng.choice([True, False]),
            "category": rng.choice(["alpha", "beta", "gamma", "delta"]),
        }

    return _payload


@dataclass
class InsertSummary:
    dataset: DatasetInfo
    rows_inserted: int
    duration_s: float


def _sample_buffer(size: int) -> Tuple[Callable[[Any], None], Callable[[], List[Any]]]:
    buffer: List[Any] = []

    def _collector(value: Any) -> None:
        if len(buffer) < size:
            buffer.append(value)
        else:
            idx = random.randint(0, len(buffer) - 1)
            buffer[idx] = value

    def _result() -> List[Any]:
        return list(buffer)

    return _collector, _result


def seed_postgres(
    engine: Engine,
    record_count: int,
    config: BenchmarkConfig,
    include_tables: Optional[Iterable[str]] = None,
) -> List[InsertSummary]:
    payload_factory = random_payload_factory(config.seed)
    tables = include_tables or POSTGRES_TABLES.keys()
    summaries: List[InsertSummary] = []

    with engine.begin() as conn:
        raw_conn = conn.connection
        cursor = raw_conn.cursor()
        for table in tables:
            cursor.execute(f"TRUNCATE TABLE {table} RESTART IDENTITY;")
            if table == "seq_id_test":
                insert_sql = "INSERT INTO seq_id_test (payload) VALUES (%s)"

                def value_builder(_: int) -> Tuple[Any]:
                    return (Json(payload_factory(_)),)

                def finalize_samples() -> List[int]:
                    rng = random.Random(config.seed)
                    sample_size = min(record_count, config.lookup_iterations)
                    population = range(1, record_count + 1)
                    return rng.sample(population, sample_size)

            elif table == "uuid_v4_test":
                insert_sql = "INSERT INTO uuid_v4_test (id, payload) VALUES (%s, %s)"

                def value_builder(_: int) -> Tuple[str, Any]:
                    return str(uuid.uuid4()), Json(payload_factory(_))

                sampler, sampler_values = _sample_buffer(2 * config.lookup_iterations)

                def finalize_samples() -> List[str]:
                    return sampler_values()[: config.lookup_iterations]

            elif table == "uuid_v7_test":
                insert_sql = "INSERT INTO uuid_v7_test (id, payload) VALUES (%s, %s)"

                def value_builder(_: int) -> Tuple[str, Any]:
                    return str(uuid7()), Json(payload_factory(_))

                sampler, sampler_values = _sample_buffer(2 * config.lookup_iterations)

                def finalize_samples() -> List[str]:
                    return sampler_values()[: config.lookup_iterations]

            elif table == "snowflake_test":
                insert_sql = "INSERT INTO snowflake_test (id, payload) VALUES (%s, %s)"

                def value_builder(_: int) -> Tuple[int, Any]:
                    return snowflake.generate(), Json(payload_factory(_))

                sampler, sampler_values = _sample_buffer(2 * config.lookup_iterations)

                def finalize_samples() -> List[int]:
                    return sampler_values()[: config.lookup_iterations]

            else:
                raise ValueError(f"Unsupported table {table}")

            if table == "seq_id_test":
                sampler = None  # type: ignore[assignment]

            start = time.perf_counter()
            batch_data: List[Tuple[Any, ...]] = []

            for i in tqdm(range(record_count), desc=f"Postgres seed {table}"):
                values = value_builder(i)
                if table != "seq_id_test":
                    sampler(values[0])  # type: ignore[misc]
                batch_data.append(values)
                if len(batch_data) >= config.batch_size:
                    execute_batch(cursor, insert_sql, batch_data)
                    batch_data.clear()
            if batch_data:
                execute_batch(cursor, insert_sql, batch_data)
            duration = time.perf_counter() - start
            summary = InsertSummary(
                dataset=DatasetInfo(
                    database="postgres",
                    id_type=table.replace("_test", ""),
                    table=table,
                    id_column="id",
                    samples=finalize_samples(),
                ),
                rows_inserted=record_count,
                duration_s=duration,
            )
            summaries.append(summary)
        cursor.close()
    return summaries


def seed_mysql(
    engine: Engine,
    record_count: int,
    config: BenchmarkConfig,
    include_tables: Optional[Iterable[str]] = None,
) -> List[InsertSummary]:
    payload_factory = random_payload_factory(config.seed)
    tables = include_tables or MYSQL_TABLES.keys()
    summaries: List[InsertSummary] = []
    connection: MySQLConnection = engine.raw_connection()  # type: ignore[attr-defined]
    cursor: MySQLCursor = connection.cursor()

    for table in tables:
        cursor.execute(f"TRUNCATE TABLE {table}")
        if table == "seq_id_test":
            insert_sql = "INSERT INTO seq_id_test (payload) VALUES (%s)"

            def value_builder(_: int) -> Tuple[str]:
                return (json.dumps(payload_factory(_)),)

            def finalize_samples() -> List[int]:
                rng = random.Random(config.seed)
                sample_size = min(record_count, config.lookup_iterations)
                population = range(1, record_count + 1)
                return rng.sample(population, sample_size)

        elif table == "uuid_v4_test":
            insert_sql = "INSERT INTO uuid_v4_test (id, payload) VALUES (%s, %s)"

            def value_builder(_: int) -> Tuple[str, str]:
                return str(uuid.uuid4()), json.dumps(payload_factory(_))

            sampler, sampler_values = _sample_buffer(2 * config.lookup_iterations)

            def finalize_samples() -> List[str]:
                return sampler_values()[: config.lookup_iterations]

        elif table == "uuid_v7_test":
            insert_sql = "INSERT INTO uuid_v7_test (id, payload) VALUES (%s, %s)"

            def value_builder(_: int) -> Tuple[str, str]:
                return str(uuid7()), json.dumps(payload_factory(_))

            sampler, sampler_values = _sample_buffer(2 * config.lookup_iterations)

            def finalize_samples() -> List[str]:
                return sampler_values()[: config.lookup_iterations]

        elif table == "snowflake_test":
            insert_sql = "INSERT INTO snowflake_test (id, payload) VALUES (%s, %s)"

            def value_builder(_: int) -> Tuple[int, str]:
                return snowflake.generate(), json.dumps(payload_factory(_))

            sampler, sampler_values = _sample_buffer(2 * config.lookup_iterations)

            def finalize_samples() -> List[int]:
                return sampler_values()[: config.lookup_iterations]

        else:
            raise ValueError(f"Unsupported table {table}")

        if table == "seq_id_test":
            sampler = None  # type: ignore[assignment]

        batch_data: List[Tuple[Any, ...]] = []
        start = time.perf_counter()
        for i in tqdm(range(record_count), desc=f"MySQL seed {table}"):
            values = value_builder(i)
            if table != "seq_id_test":
                sampler(values[0])  # type: ignore[misc]
            batch_data.append(values)
            if len(batch_data) >= config.batch_size:
                cursor.executemany(insert_sql, batch_data)
                connection.commit()
                batch_data.clear()
        if batch_data:
            cursor.executemany(insert_sql, batch_data)
            connection.commit()
        summary = InsertSummary(
            dataset=DatasetInfo(
                database="mysql",
                id_type=table.replace("_test", ""),
                table=table,
                id_column="id",
                samples=finalize_samples(),
            ),
            rows_inserted=record_count,
            duration_s=time.perf_counter() - start,
        )
        summaries.append(summary)
    cursor.close()
    connection.close()
    return summaries


def seed_redis(
    client: redis.Redis,
    datasets: Sequence[DatasetInfo],
    config: BenchmarkConfig,
) -> List[DatasetInfo]:
    pipeline = client.pipeline(transaction=False)
    redis_datasets: List[DatasetInfo] = []
    for dataset in datasets:
        samples: List[str] = []
        for key in tqdm(
            dataset.samples[: config.lookup_iterations],
            desc=f"Redis load {dataset.id_type}",
        ):
            redis_key = f"{dataset.id_type}:{key}"
            pipeline.set(redis_key, "payload")
            samples.append(redis_key)
        redis_datasets.append(
            DatasetInfo(
                database="redis",
                id_type=dataset.id_type,
                table="",
                id_column="key",
                samples=samples,
            )
        )
    pipeline.execute()
    return redis_datasets


# ---------------------------------------------------------------------------
# Benchmark execution
# ---------------------------------------------------------------------------


def measure_operation(
    func: Callable[[Any], Any],
    inputs: Sequence[Any],
    label: str,
    config: BenchmarkConfig,
    show_progress: bool = True,
) -> ResultRow:
    timings: List[float] = []
    iterator = inputs
    progress = tqdm(iterator, desc=label) if show_progress else inputs
    for item in progress:
        start = time.perf_counter()
        func(item)
        timings.append((time.perf_counter() - start) * 1000)
    arr = np.array(timings, dtype=float)
    return ResultRow(
        database=label.split("::")[0],
        id_type=label.split("::")[1],
        operation=label.split("::")[2] if len(label.split("::")) > 2 else "lookup",
        avg_ms=float(np.mean(arr)),
        p95_ms=float(np.percentile(arr, 95)),
        min_ms=float(np.min(arr)),
        max_ms=float(np.max(arr)),
        lookups=len(timings),
    )


def fetch_function(engine: Engine, table: str, id_column: str) -> Callable[[Any], None]:
    stmt = text(f"SELECT payload FROM {table} WHERE {id_column} = :id")

    def _fetch(value: Any) -> None:
        with engine.connect() as conn:
            conn.execute(stmt, {"id": value}).fetchone()

    return _fetch


def fetch_with_prepared(
    engine: Engine, table: str, id_column: str
) -> Callable[[Any], None]:
    def _fetch(value: Any) -> None:
        with engine.connect() as conn:
            result = conn.execute(
                text(f"SELECT payload FROM {table} WHERE {id_column} = :id"),
                {"id": value},
            )
            result.first()

    return _fetch


def fetch_mysql(engine: Engine, table: str, id_column: str) -> Callable[[Any], None]:
    sql = f"SELECT payload FROM {table} WHERE {id_column} = %s"

    def _fetch(value: Any) -> None:
        conn = engine.raw_connection()
        cursor = conn.cursor()
        cursor.execute(sql, (value,))
        cursor.fetchone()
        cursor.close()
        conn.close()

    return _fetch


def fetch_redis(client: redis.Redis) -> Callable[[Any], None]:
    def _fetch(key: Any) -> None:
        client.get(key)

    return _fetch


def results_to_frame(results: Sequence[ResultRow]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "database": r.database,
                "id_type": r.id_type,
                "operation": r.operation,
                "avg_ms": r.avg_ms,
                "p95_ms": r.p95_ms,
                "min_ms": r.min_ms,
                "max_ms": r.max_ms,
                "lookups": r.lookups,
            }
            for r in results
        ]
    )


# ---------------------------------------------------------------------------
# Secondary experiment helpers (PostgreSQL only)
# ---------------------------------------------------------------------------


def postgres_uuid_workload(
    engine: Engine,
    table_name: str,
    id_version: str,
    iterations: int,
    config: BenchmarkConfig,
) -> Dict[str, ResultRow]:
    metadata = sa.MetaData()
    table = sa.Table(
        table_name,
        metadata,
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("payload", postgresql.JSONB, nullable=False),
        extend_existing=True,
    )
    metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE TABLE {table_name} RESTART IDENTITY;"))
    payload_factory = random_payload_factory(config.seed)
    insert_stmt = table.insert()

    # INSERT benchmark
    inserts: List[Dict[str, Any]] = []
    for i in range(iterations):
        uid = str(uuid.uuid4()) if id_version == "uuid_v4" else str(uuid7())
        inserts.append({"id": uid, "payload": payload_factory(i)})
    with engine.begin() as conn:
        start = time.perf_counter()
        conn.execute(insert_stmt, inserts)
        insert_duration = (time.perf_counter() - start) * 1000

    # SELECT benchmark
    select_stmt = table.select().where(table.c.id == sa.bindparam("id"))
    ids = [row["id"] for row in inserts[: config.lookup_iterations]]
    timings = []
    for value in ids:
        with engine.begin() as conn:
            start = time.perf_counter()
            conn.execute(select_stmt, {"id": value}).first()
            timings.append((time.perf_counter() - start) * 1000)

    # ORDER BY benchmark
    with engine.begin() as conn:
        start = time.perf_counter()
        conn.execute(table.select().order_by(table.c.id).limit(1000)).fetchall()
        order_duration = (time.perf_counter() - start) * 1000

    return {
        "insert": ResultRow(
            database="postgres",
            id_type=id_version,
            operation="insert",
            avg_ms=insert_duration / max(1, len(inserts)),
            p95_ms=insert_duration,
            min_ms=insert_duration,
            max_ms=insert_duration,
            lookups=len(inserts),
        ),
        "select": ResultRow(
            database="postgres",
            id_type=id_version,
            operation="select",
            avg_ms=float(np.mean(timings)),
            p95_ms=float(np.percentile(timings, 95)),
            min_ms=float(np.min(timings)),
            max_ms=float(np.max(timings)),
            lookups=len(timings),
        ),
        "order": ResultRow(
            database="postgres",
            id_type=id_version,
            operation="order",
            avg_ms=order_duration,
            p95_ms=order_duration,
            min_ms=order_duration,
            max_ms=order_duration,
            lookups=1000,
        ),
    }
