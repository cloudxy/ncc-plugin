from contextlib import asynccontextmanager
from urllib.parse import unquote

from sqlalchemy.dialects.postgresql.psycopg import PGDialect_psycopg
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from ncc_shared.database import postgres_url


def driver_url(url):
    """Decode the URI database path once; SQLAlchemy decodes credentials but not this path."""
    parsed = make_url(postgres_url(url))
    return parsed.set(database=unquote(parsed.database))


def connection_parameters(url):
    """Use the application's exact driver interpretation, including TLS and Unix sockets."""
    _, parameters = PGDialect_psycopg().create_connect_args(driver_url(url))
    return parameters


def database(url: str):
    url = driver_url(url)
    engine = create_async_engine(url, pool_pre_ping=True, pool_size=8, max_overflow=4)
    return engine, async_sessionmaker(engine, expire_on_commit=False)


@asynccontextmanager
async def transaction(factory):
    async with factory() as session, session.begin():
        yield session
