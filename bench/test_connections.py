import asyncio
import socket
import time

import asyncpg
from sqlalchemy import NullPool
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import sqlalchemy as sa


def log(label, t0, t1, t2, t3):
    pre_connect = (t1 - t0) / 1000000
    connect = (t2 - t1) / 1000000
    execute = (t3 - t2) / 1000000
    total = (t3 - t1) / 1000000
    print(
        f"""
{label}:
Pre: {pre_connect} ms
Connect: {connect} ms
Execute: {execute} ms
Total: {total} ms
"""

    )


async def sqla_null(creds):
    t0 = time.perf_counter_ns()
    engine = create_async_engine(
        f'postgresql+asyncpg://{creds}',
        poolclass=NullPool,
        connect_args={
            'timeout': 1,
            'command_timeout': 5,
            'server_settings': {'application_name': 'test'}
        }
    )
    Session = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    t1 = time.perf_counter_ns()
    async with Session() as conn:
        t2 = time.perf_counter_ns()
        await conn.execute(sa.text('select 1;'))
        t3 = time.perf_counter_ns()
    log('sqla null pool', t0, t1, t2, t3)


async def sqla_pool(creds, min_size):
    t0 = time.perf_counter_ns()
    engine = create_async_engine(
        f'postgresql+asyncpg://{creds}',
        pool_size=min_size,
        connect_args={
            'timeout': 1,
            'command_timeout': 5,
            'server_settings': {'application_name': 'test'}
        }
    )

    t1 = time.perf_counter_ns()
    async with engine.connect() as conn:
        t2 = time.perf_counter_ns()
        await conn.execute(sa.text('select 1;'))
        t3 = time.perf_counter_ns()
    log(f'sqla pool {min_size=}', t0, t1, t2, t3)


async def aspg_raw(creds):
    t0 = time.perf_counter_ns()
    t1 = time.perf_counter_ns()
    conn = await asyncpg.connect(f'postgres://{creds}')
    t2 = time.perf_counter_ns()
    await conn.execute('select 1;')
    t3 = time.perf_counter_ns()
    log('asyncpg raw', t0, t1, t2, t3)


async def aspg_pool(creds, min_size: int):
    t0 = time.perf_counter_ns()
    pool = await asyncpg.create_pool(
        f'postgres://{creds}',
        min_size=min_size,
    )
    t1 = time.perf_counter_ns()
    async with pool.acquire() as conn:
        t2 = time.perf_counter_ns()
        await conn.execute('select 1;')
        t3 = time.perf_counter_ns()
    log(f'asyncpg pool {min_size=}', t0, t1, t2, t3)


def test_raw_socket(host: str, port: int):
    t0 = time.perf_counter_ns()
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    t1 = time.perf_counter_ns()
    s.connect((host, port))
    t2 = time.perf_counter_ns()
    t3 = time.perf_counter_ns()
    s.close()
    log(f'socket {host}:{port}', t0, t1, t2, t3)


async def _main(creds):
    await sqla_null(creds)
    await sqla_pool(creds, 0)
    await sqla_pool(creds, 1)
    await aspg_raw(creds)
    await aspg_pool(creds, 0)
    await aspg_pool(creds, 1)


def test_pg_connections():
    creds = input('creds:')
    asyncio.run(_main(creds))


print(
    """
test_raw_socket('ip/domain', port)
... 

test_pg_connections()
creds: postgres:postgres@localhost:5432/postgres
...
    """
)
