from fastapi.params import Depends
from typing_extensions import Annotated
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from it_career_navigator.config import settings

SQLALCHEMY_DATABASE_URL = settings.db_url


engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass


async def get_db():
    async with SessionLocal() as session:
        yield session


Get_DB = Annotated[AsyncSession, Depends(get_db)]