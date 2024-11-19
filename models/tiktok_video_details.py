# models/tiktok_video_details.py

from sqlalchemy import Column, String, Integer, Boolean, Text, DateTime, BigInteger
from sqlalchemy.sql import func
from . import Base

class TikTokVideoDetails(Base):
    __tablename__ = 'tiktok_video_details'

    video_id = Column(BigInteger, primary_key=True, autoincrement=True)  # 自增ID
    tiktok_video_id = Column(String(50), nullable=False)  # TikTok平台的唯一视频ID
    author_id = Column(String(50), nullable=False)  # 视频作者ID
    author_nickname = Column(String(100))  # 视频作者昵称
    author_avatar_larger = Column(String(255))  # 大头像URL
    author_avatar_medium = Column(String(255))  # 中头像URL
    author_avatar_thumb = Column(String(255))  # 小头像URL
    description = Column(Text)  # 视频描述
    created_time = Column(BigInteger)  # 创建时间戳
    original_item = Column(Boolean, default=False)  # 是否为原创
    private_item = Column(Boolean, default=False)  # 是否为私密
    duet_enabled = Column(Boolean, default=False)  # 是否允许合拍
    stitch_enabled = Column(Boolean, default=False)  # 是否允许拼接
    share_enabled = Column(Boolean, default=True)  # 是否允许分享

    # 视频统计数据
    play_count = Column(Integer, default=0)  # 播放次数
    comment_count = Column(Integer, default=0)  # 评论次数
    digg_count = Column(Integer, default=0)  # 点赞次数
    share_count = Column(Integer, default=0)  # 分享次数
    collect_count = Column(Integer, default=0)  # 收藏次数
    repost_count = Column(Integer, default=0)  # 转发次数

    # 音乐信息
    music_id = Column(String(50))  # 音乐ID
    music_author = Column(String(100))  # 音乐作者
    music_title = Column(String(255))  # 音乐标题
    music_cover_larger = Column(String(255))  # 音乐封面大图
    music_cover_medium = Column(String(255))  # 音乐封面中图
    music_cover_thumb = Column(String(255))  # 音乐封面小图
    music_duration = Column(Integer)  # 音乐时长（秒）

    # 视频URL信息
    video_url = Column(String(255))  # 视频播放地址
    video_download_addr = Column(String(255))  # 视频下载地址
    video_bitrate = Column(Integer)  # 视频比特率
    video_quality = Column(String(50))  # 视频质量
    video_definition = Column(String(50))  # 视频分辨率
    video_format = Column(String(10))  # 视频格式
    video_width = Column(Integer)  # 视频宽度
    video_height = Column(Integer)  # 视频高度

    created_at = Column(DateTime, server_default=func.now())  # 记录创建时间
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())  # 记录更新时间
