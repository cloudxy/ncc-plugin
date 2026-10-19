from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


def database(url: str):
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    if not url.startswith("postgresql+psycopg://"):
        raise ValueError("NCC数据服务只接受PostgreSQL/Psycopg连接")
    engine = create_async_engine(url, pool_pre_ping=True, pool_size=8, max_overflow=4)
    return engine, async_sessionmaker(engine, expire_on_commit=False)


@asynccontextmanager
async def transaction(factory):
    async with factory() as session, session.begin():
        yield session
