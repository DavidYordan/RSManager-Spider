# models/tiktok_account.py

from sqlalchemy import Column, String, Integer, Boolean, Text, DateTime, BigInteger
from sqlalchemy.sql import func
from . import Base

class TikTokAccount(Base):
    __tablename__ = 'tiktok_account'

    tiktok_account = Column(String(100), primary_key=True)  # TikTok账号
    tiktok_id = Column(String(50))  # TikTok平台的用户ID
    unique_id = Column(String(50))  # 用户唯一ID
    nickname = Column(String(100))  # 用户昵称
    avatar_larger = Column(Text)  # 大图头像URL
    avatar_medium = Column(Text)  # 中图头像URL
    avatar_thumb = Column(Text)  # 小图头像URL
    signature = Column(Text)  # 用户签名
    verified = Column(Boolean)  # 是否认证
    sec_uid = Column(String(255))  # 安全UID
    private_account = Column(Boolean)  # 是否为私密账户
    following_visibility = Column(Integer)  # 关注可见性设置
    comment_setting = Column(Integer)  # 评论设置
    duet_setting = Column(Integer)  # 合拍设置
    stitch_setting = Column(Integer)  # 拼接设置
    download_setting = Column(Integer)  # 下载设置
    profile_embed_permission = Column(Integer)  # 个人资料嵌入权限
    profile_tab_show_playlist_tab = Column(Boolean)  # 是否展示播放列表标签
    commerce_user = Column(Boolean)  # 是否为商业用户
    tt_seller = Column(Boolean)  # 是否为TikTok卖家
    relation = Column(Integer)  # 用户关系
    is_ad_virtual = Column(Boolean)  # 是否为虚拟广告用户
    is_embed_banned = Column(Boolean)  # 是否禁用嵌入
    open_favorite = Column(Boolean)  # 是否开放收藏
    nick_name_modify_time = Column(BigInteger)  # 昵称修改时间戳
    can_exp_playlist = Column(Boolean)  # 是否可以播放列表
    secret = Column(Boolean)  # 是否为私密账户
    ftc = Column(Boolean)  # 是否为FTC
    link = Column(Text)  # 用户链接
    risk = Column(Integer)  # 风险等级

    # 统计信息字段
    digg_count = Column(Integer)  # 点赞数
    follower_count = Column(Integer)  # 粉丝数
    following_count = Column(Integer)  # 关注数
    friend_count = Column(Integer)  # 好友数
    heart_count = Column(Integer)  # 获赞总数
    video_count = Column(Integer)  # 视频总数

    created_at = Column(DateTime, server_default=func.now())  # 记录创建时间
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())  # 记录更新时间
    comments = Column(String(64))  # 备注
