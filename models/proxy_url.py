# /models/proxy_url.py

from sqlalchemy import Column, String, Integer, DateTime, BigInteger, Float, Boolean, Computed
from sqlalchemy.sql import func
from . import Base

class ProxyUrl(Base):
    __tablename__ = 'proxy_url'

    id = Column(BigInteger, primary_key=True, autoincrement=True)  # 自增ID
    subscribe_id = Column(BigInteger, nullable=False)  # 订阅ID
    url = Column(String(255), nullable=False)  # 代理链接
    type = Column(String(50), nullable=False)  # 代理类型
    current_port = Column(Integer, nullable=False, default=0)  # 当前端口
    is_using = Column(Boolean, default=False)  # 是否正在使用
    created_at = Column(DateTime, server_default=func.now())  # 记录创建时间
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())  # 记录更新时间
    current_delay = Column(Integer, default=0)  # 当前延迟
    delay_count = Column(BigInteger, default=0)  # 延迟次数
    avg_delay = Column(Float, default=0)  # 平均延迟
    success_count = Column(BigInteger, default=0)  # 成功次数
    fail_count = Column(BigInteger, default=0)  # 失败次数
    success_rate = Column(
        Float,
        Computed(
            "CASE WHEN success_count + fail_count = 0 THEN 0 ELSE success_count / (success_count + fail_count) END",
            persisted=True
        ),
        nullable=True
    )  # 生成列
    comments = Column(String(255))  # 备注信息