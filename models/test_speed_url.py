# models/test_speed_url.py

from sqlalchemy import Column, BigInteger, String, Date, Boolean
from sqlalchemy.sql import func
from . import Base

class TestSpeedUrl(Base):
    __tablename__ = 'test_speed_url'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    url = Column(String(255), nullable=False)
    success_count = Column(BigInteger, default=0)
    fail_count = Column(BigInteger, default=0)
    comments = Column(String(255))