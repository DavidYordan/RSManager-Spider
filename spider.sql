DROP TABLE IF EXISTS `tiktok_account`;
CREATE TABLE tiktok_account (
    tiktok_account VARCHAR(100) PRIMARY KEY, -- TikTok账号
    tiktok_id VARCHAR(50), -- TikTok平台的用户ID
    unique_id VARCHAR(50), -- TikTok平台的唯一用户ID
    nickname VARCHAR(100), -- 用户昵称
    avatar_larger TEXT, -- 大图头像URL
    avatar_medium TEXT, -- 中图头像URL
    avatar_thumb TEXT, -- 小图头像URL
    signature TEXT, -- 用户签名
    verified BOOLEAN, -- 是否认证
    sec_uid VARCHAR(255), -- 安全UID
    private_account BOOLEAN, -- 是否为私密账户
    following_visibility INT, -- 关注可见性设置
    comment_setting INT, -- 评论设置
    duet_setting INT, -- 合拍设置
    stitch_setting INT, -- 拼接设置
    download_setting INT, -- 下载设置
    profile_embed_permission INT, -- 个人资料嵌入权限
    profile_tab_show_playlist_tab BOOLEAN, -- 是否展示播放列表标签
    commerce_user BOOLEAN, -- 是否为商业用户
    tt_seller BOOLEAN, -- 是否为TikTok卖家
    relation INT, -- 用户关系
    is_ad_virtual BOOLEAN, -- 是否为虚拟广告用户
    is_embed_banned BOOLEAN, -- 是否禁用嵌入
    open_favorite BOOLEAN, -- 是否开放收藏
    nick_name_modify_time BIGINT, -- 昵称修改时间戳
    can_exp_playlist BOOLEAN, -- 是否可以播放列表
    secret Boolean, -- 是否为私密账户
    ftc Boolean, -- 是否为FTC
    link TEXT, -- 用户链接
    risk BIGINT, -- 风险等级

    -- 统计信息字段
    digg_count INT, -- 点赞数
    follower_count INT, -- 粉丝数
    following_count INT, -- 关注数
    friend_count INT, -- 好友数
    heart_count INT, -- 获赞总数
    video_count INT, -- 视频总数

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP, -- 记录创建时间
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, -- 记录更新时间
    comments VARCHAR(64) -- 备注
);

DROP TABLE IF EXISTS `tiktok_video_details`;
CREATE TABLE tiktok_video_details (
    tiktok_video_id VARCHAR(50) PRIMARY KEY, -- TikTok平台的唯一视频ID
    author_id VARCHAR(50) NOT NULL, -- 视频作者ID
    AIGCDescription TEXT,
    CategoryType INT,
    backendSourceEventTracking TEXT,
    collected BOOLEAN,
    createTime BIGINT,
    video_desc TEXT,
    digged BOOLEAN,
    diversificationId INT,
    duetDisplay INT,
    duetEnabled BOOLEAN,
    forFriend BOOLEAN,
    itemCommentStatus INT,
    officalItem BOOLEAN,
    originalItem BOOLEAN,
    privateItem BOOLEAN,
    secret BOOLEAN,
    shareEnabled BOOLEAN,
    stitchDisplay INT,
    stitchEnabled BOOLEAN,

    -- item_control
    can_repost BOOLEAN,

    -- statsV2
    collectCount INT,
    commentCount INT,
    diggCount INT,
    playCount INT,
    repostCount INT,
    shareCount INT,

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

DROP TABLE IF EXISTS tiktok_relationship;
CREATE TABLE tiktok_relationship (
    record_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    tiktok_account VARCHAR(100) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE,
    status BOOLEAN NOT NULL DEFAULT FALSE,
    creater_id BIGINT NOT NULL,
    updated_at DATETIME
);

DROP TABLE IF EXISTS subscribe_url;
CREATE TABLE subscribe_url (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    url VARCHAR(255) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    comments VARCHAR(255)
);

DROP TABLE IF EXISTS proxy_url;
CREATE TABLE proxy_url (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    subscribe_id BIGINT NOT NULL,
    url VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL,
    is_using BOOLEAN NOT NULL DEFAULT FALSE,
    current_port INT NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    current_delay INT DEFAULT 0,
    delay_count BIGINT DEFAULT 0,
    avg_delay FLOAT DEFAULT 0,
    success_count BIGINT DEFAULT 0,
    fail_count BIGINT DEFAULT 0,
    success_rate FLOAT AS (
        CASE
            WHEN success_count + fail_count = 0 THEN 0
            ELSE success_count / (success_count + fail_count)
        END
    ) STORED,
    comments TEXT
);

DROP TRIGGER IF EXISTS trg_proxy_url_before_update;
DELIMITER $$
CREATE TRIGGER trg_proxy_url_before_update
BEFORE UPDATE ON proxy_url
FOR EACH ROW
BEGIN
    IF NEW.current_delay IS NOT NULL THEN
        SET @old_delay_count = IFNULL(OLD.delay_count, 0);
        SET @old_avg_delay = IFNULL(OLD.avg_delay, 0);

        SET NEW.delay_count = @old_delay_count + 1;

        SET NEW.avg_delay = (@old_avg_delay * @old_delay_count + NEW.current_delay) / NEW.delay_count;
    END IF;
END$$
DELIMITER ;

DROP TABLE IF EXISTS test_speed_url;
CREATE TABLE test_speed_url (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    url VARCHAR(255) NOT NULL,
    success_count BIGINT DEFAULT 0,
    fail_count BIGINT DEFAULT 0,
    comments VARCHAR(255)
);

INSERT INTO test_speed_url (url, comments) VALUES
    ("http://www.gstatic.com/generate_204", "Google"),
    ("http://www.google-analytics.com/generate_204", "Google"),
    ("http://www.google.com/generate_204", "Google"),
    ("http://connectivitycheck.gstatic.com/generate_204", "Google"),
    ("http://captive.apple.com", "Apple"),
    ("http://www.apple.com/library/test/success.html", "Apple"),
    ("http://www.msftconnecttest.com/connecttest.txt", "Microsoft"),
    ("http://cp.cloudflare.com/", "CloudFlare"),
    ("http://detectportal.firefox.com/success.txt", "Mozilla");