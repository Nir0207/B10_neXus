from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator
from typing import Any

import asyncpg
from neo4j import AsyncDriver, AsyncGraphDatabase, AsyncSession

POSTGRES_URL = os.getenv("POSTGRES_URL", "postgresql://user:password@localhost:5432/bionexus")
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

# Connection pools
pg_pool: asyncpg.pool.Pool | None = None
neo4j_driver: AsyncDriver | None = None
logger = logging.getLogger(__name__)

async def init_db() -> None:
    global pg_pool, neo4j_driver
    try:
        pg_pool = await asyncpg.create_pool(dsn=POSTGRES_URL, min_size=1, max_size=10)
        neo4j_driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    except Exception as exc:
        logger.warning("Database initialization failed. API will return upstream errors until recovered: %s", exc)

async def close_db() -> None:
    global pg_pool, neo4j_driver
    if pg_pool is not None:
        await pg_pool.close()
    if neo4j_driver is not None:
        await neo4j_driver.close()

async def get_postgres_connection() -> AsyncIterator[asyncpg.Connection | None]:
    if pg_pool is None:
        yield None
        return
    async with pg_pool.acquire() as connection:
        yield connection

async def get_neo4j_session() -> AsyncIterator[AsyncSession | None]:
    if neo4j_driver is None:
        yield None
        return
    async with neo4j_driver.session() as session:
        yield session
