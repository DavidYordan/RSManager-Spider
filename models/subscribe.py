# /models/subscribe.py

from sqlalchemy import Column, String, DateTime, BigInteger
from sqlalchemy.sql import func
from . import Base

class SubscribeUrl(Base):
    __tablename__ = 'subscribe_url'

    id = Column(BigInteger, primary_key=True, autoincrement=True)  # 自增ID
    url = Column(String(255), nullable=False)  # 订阅链接
    created_at = Column(DateTime, server_default=func.now())  # 记录创建时间
    comments = Column(String(255))  # 备注