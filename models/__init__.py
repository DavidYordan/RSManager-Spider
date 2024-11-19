# models/__init__.py

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from config.config import Config

# 异步数据库连接字符串
DATABASE_URL = f"mysql+aiomysql://{Config.DB_USER}:{Config.DB_PASSWORD}@{Config.DB_HOST}:{Config.DB_PORT}/{Config.DB_NAME}?charset=utf8mb4"

# 创建异步引擎
async_engine = create_async_engine(DATABASE_URL, echo=True)

# 创建异步会话
AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

# 基类
Base = declarative_base()
