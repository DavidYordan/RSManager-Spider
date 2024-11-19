# /models/proxy_url.py

from sqlalchemy import Column, String, Integer, DateTime, BigInteger
from sqlalchemy.sql import func
from . import Base

class ProxyUrl(Base):
    __tablename__ = 'proxy_url'

    id = Column(BigInteger, primary_key=True, autoincrement=True)  # 自增ID
    subscribe_id = Column(BigInteger, nullable=False)  # 订阅ID
    url = Column(String(255), nullable=False)  # 代理链接
    type = Column(String(50), nullable=False)  # 代理类型
    created_at = Column(DateTime, server_default=func.now())  # 记录创建时间
    comments = Column(String(255))  # 备注