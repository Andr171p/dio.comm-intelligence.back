from ddf.infra.database.sqlalchemy import PostgresConfig
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

postgres_config = PostgresConfig()

engine = create_async_engine(
    postgres_config.uri,
    pool_size=postgres_config.pool_resize,
    max_overflow=postgres_config.max_overflow,
    pool_timeout=postgres_config.pool_timeout,
    echo=postgres_config.echo,
)
sessionmaker = async_sessionmaker(engine, expire_on_commit=False)

__all__ = ["engine", "postgres_config", "sessionmaker"]
