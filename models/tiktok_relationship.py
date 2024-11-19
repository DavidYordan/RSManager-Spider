# models/tiktok_relationship.py

from sqlalchemy import Column, BigInteger, String, Date, Boolean
from sqlalchemy.sql import func
from . import Base

class TikTokRelationship(Base):
    __tablename__ = 'tiktok_relationship'

    record_id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)
    tiktok_account = Column(String(100), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date)
    status = Column(Boolean, nullable=False, default=False)
    creater_id = Column(BigInteger, nullable=False)
