# models/tiktok_account.py

from sqlalchemy import Column, String, Integer, Boolean, Text, DateTime, BigInteger
from sqlalchemy.sql import func
from . import Base

class TikTokAccount(Base):
    __tablename__ = 'tiktok_account'

    tiktok_account = Column(String(100), primary_key=True)  # TikTok账号
    tiktok_id = Column(String(50))  # TikTok平台的用户ID
    nickname = Column(String(100))  # 用户昵称
    avatar_larger = Column(String(255))  # 大图头像URL
    avatar_medium = Column(String(255))  # 中图头像URL
    avatar_thumb = Column(String(255))  # 小图头像URL
    signature = Column(Text)  # 用户签名
    verified = Column(Boolean, default=False)  # 是否认证
    sec_uid = Column(String(255))  # 安全UID
    private_account = Column(Boolean, default=False)  # 是否为私密账户
    following_visibility = Column(Integer, default=0)  # 关注可见性设置
    comment_setting = Column(Integer, default=0)  # 评论设置
    duet_setting = Column(Integer, default=0)  # 合拍设置
    stitch_setting = Column(Integer, default=0)  # 拼接设置
    download_setting = Column(Integer, default=0)  # 下载设置
    profile_embed_permission = Column(Integer, default=0)  # 个人资料嵌入权限
    profile_tab_show_playlist_tab = Column(Boolean, default=False)  # 是否展示播放列表标签
    commerce_user = Column(Boolean, default=False)  # 是否为商业用户
    tt_seller = Column(Boolean, default=False)  # 是否为TikTok卖家
    relation = Column(Integer, default=0)  # 用户关系
    is_ad_virtual = Column(Boolean, default=False)  # 是否为虚拟广告用户
    is_embed_banned = Column(Boolean, default=False)  # 是否禁用嵌入
    open_favorite = Column(Boolean, default=False)  # 是否开放收藏
    nick_name_modify_time = Column(BigInteger)  # 昵称修改时间戳
    can_exp_playlist = Column(Boolean, default=False)  # 是否可以播放列表

    # 统计信息字段
    digg_count = Column(Integer, default=0)  # 点赞数
    follower_count = Column(Integer, default=0)  # 粉丝数
    following_count = Column(Integer, default=0)  # 关注数
    friend_count = Column(Integer, default=0)  # 好友数
    heart_count = Column(Integer, default=0)  # 获赞总数
    video_count = Column(Integer, default=0)  # 视频总数

    created_at = Column(DateTime, server_default=func.now())  # 记录创建时间
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())  # 记录更新时间
    comments = Column(String(255))  # 备注
