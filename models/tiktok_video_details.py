# models/tiktok_video_details.py

from sqlalchemy import Column, String, Integer, Boolean, Text, DateTime, BigInteger, TEXT
from sqlalchemy.sql import func
from . import Base

class TikTokVideoDetails(Base):
    __tablename__ = 'tiktok_video_details'

    tiktok_video_id = Column(String(50), primary_key=True)  # TikTok视频ID
    author_id = Column(String(50), nullable=False)  # 视频作者ID
    AIGCDescription = Column(TEXT, comment="AIGC 描述")
    CategoryType = Column(Integer, comment="分类类型")
    backendSourceEventTracking = Column(TEXT, comment="后端源事件跟踪")
    collected = Column(Boolean, comment="是否已收藏")
    createTime = Column(BigInteger, comment="创建时间（Unix 时间戳）")
    video_desc = Column(Text, comment="视频描述")
    digged = Column(Boolean, comment="是否被点赞")
    diversificationId = Column(Integer, comment="多样化 ID")
    duetDisplay = Column(Integer, comment="Duet 显示状态")
    duetEnabled = Column(Boolean, comment="是否启用 Duet")
    forFriend = Column(Boolean, comment="是否仅对好友可见")
    itemCommentStatus = Column(Integer, comment="评论状态")
    officalItem = Column(Boolean, comment="是否为官方项目")
    originalItem = Column(Boolean, comment="是否为原创项目")
    privateItem = Column(Boolean, comment="是否为私密项目")
    secret = Column(Boolean, comment="是否为秘密项目")
    shareEnabled = Column(Boolean, comment="是否启用分享")
    stitchDisplay = Column(Integer, comment="Stitch 显示状态")
    stitchEnabled = Column(Boolean, comment="是否启用 Stitch")

    # item_control
    can_repost = Column(Boolean)

    # statsV2
    collectCount = Column(Integer)
    commentCount = Column(Integer)
    diggCount = Column(Integer)
    playCount = Column(Integer)
    repostCount = Column(Integer)
    shareCount = Column(Integer)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="记录创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="记录更新时间")
